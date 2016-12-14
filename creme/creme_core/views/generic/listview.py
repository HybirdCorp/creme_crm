# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from json import loads as json_load, dumps as json_dump
import logging

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.http import Http404
from django.shortcuts import render
from django.utils.translation import ugettext as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.core.entity_cell import EntityCellActions
from creme.creme_core.core.paginator import FlowPaginator, LastPage
from creme.creme_core.gui.listview import ListViewState
from creme.creme_core.models import CremeEntity
from creme.creme_core.models.entity_filter import EntityFilterList
from creme.creme_core.models.header_filter import HeaderFilterList
from creme.creme_core.utils import get_ct_or_404
from creme.creme_core.utils.queries import get_q_from_dict
from .popup import inner_popup


logger = logging.getLogger(__name__)


class NoHeaderFilterAvailable(Exception):
    pass


def _clean_value(value, converter, default=None):
    try:
        return converter(value)
    except Exception as e:
        if default is not None:
            return default

        raise e


def _build_entity_queryset(request, model, list_view_state, extra_q, entity_filter, header_filter):
    filtered = False
    use_distinct = False
    queryset = model.objects.filter(is_deleted=False)

    if entity_filter:
        filtered = True
        queryset = entity_filter.filter(queryset)

    if extra_q:
        try:
            queryset = queryset.filter(extra_q)
        except Exception:
            logger.exception('Error when build the search queryset. Invalid q_filter.')
        else:
            filtered = True
            use_distinct = True

    list_view_state.extra_q = extra_q   # TODO: only if valid ?

    # TODO: method in ListViewState that returns the improved queryset
    lv_state_q = list_view_state.get_q_with_research(model, header_filter.cells)
    try:
        queryset = queryset.filter(lv_state_q)
    except Exception:
        logger.exception('Error when build the search queryset.')
    else:
        if lv_state_q:
            filtered = True
            use_distinct = True

    user = request.user
    # queryset = EntityCredentials.filter(user, queryset).distinct()
    queryset = EntityCredentials.filter(user, queryset)
    # queryset = list_view_state.sort_query(queryset)

    if use_distinct:
        queryset = queryset.distinct()

    # If the query does not use the real entities' specific fields to filter,
    # we perform a query on CremeEntity & so we avoid a JOIN.
    count = queryset.count() if filtered else \
            EntityCredentials.filter_entities(
                    user,
                    CremeEntity.objects.filter(
                         is_deleted=False,
                         entity_type=ContentType.objects.get_for_model(model),
                        ),
                    as_model=model,
                ).count()

    # return queryset
    return queryset, count


# def _build_entities_page(request, list_view_state, queryset, size):
#     paginator = Paginator(queryset, size)
#
#     try:
#         page = int(request.POST.get('page'))
#         list_view_state.page = page
#     except (ValueError, TypeError):
#         page = list_view_state.page or 1
#
#     try:
#         entities_page = paginator.page(page)
#     except (EmptyPage, InvalidPage):
#         entities_page = paginator.page(paginator.num_pages)
#
#     return entities_page
def _build_entities_page(request, list_view_state, queryset, size, count, ordering, fast_mode=False):
    if not fast_mode:
        paginator = Paginator(queryset, size)
        paginator._count = count

        try:
            page = int(request.POST['page'])
        except (KeyError, ValueError, TypeError):
            page = list_view_state.page or 1

        try:
            entities_page = paginator.page(page)
        except (EmptyPage, InvalidPage):
            entities_page = paginator.page(paginator.num_pages)

        list_view_state.page = entities_page.number
    else:
        paginator = FlowPaginator(queryset=queryset, key=ordering[0], per_page=size, count=count)
        page_str = request.POST.get('page') or str(list_view_state.page)

        try:
            page_info = json_load(page_str)
        except ValueError:
            page_info = None
        else:
            if not isinstance(page_info, dict):
                page_info = None

        try:
            entities_page = paginator.page(page_info)
        except LastPage:
            entities_page = paginator.last_page()
        except InvalidPage:
            entities_page = paginator.page()

        list_view_state.page = json_dump(entities_page.info())

    return entities_page


def _build_extrafilter(request, extra_filter=None):
    json_q_filter = request.GET.get('q_filter')
    q_filter_as_dict = _clean_value(json_q_filter, json_load, {})

    if not q_filter_as_dict:
        json_q_filter = request.POST.get('q_filter', '{}')
        q_filter_as_dict = _clean_value(json_q_filter, json_load, {})

    q_filter = get_q_from_dict(q_filter_as_dict)

    if extra_filter is not None:
        q_filter &= extra_filter

    return json_q_filter, q_filter


def _select_entityfilter(request, entity_filters, default_filter):
    efilter_id = request.GET.get('filter')

    if not efilter_id:
        efilter_id = request.POST.get('filter', default_filter)

    return entity_filters.select_by_id(efilter_id)


def list_view_content(request, model, hf_pk='', extra_dict=None,
                      template='creme_core/generics/list_entities.html',
                      show_actions=True, extra_q=None, o2m=False, post_process=None,
                      content_template='creme_core/frags/list_view_content.html',
                     ):
    """ Generic list_view wrapper / generator
    Accept only CremeEntity model and subclasses
    @param post_process: Function that takes the template context and the
                         request as parameters (so you can modify the context).
    """
    assert issubclass(model, CremeEntity), '%s is not a subclass of CremeEntity' % model

    POST_get = request.POST.get
    current_lvs = ListViewState.get_state(request)

    if current_lvs is None:
        current_lvs = ListViewState.build_from_request(request)  # TODO: move to ListViewState.get_state() ???

    PAGE_SIZES = settings.PAGE_SIZES

    try:
        rows = int(POST_get('rows'))
    except (ValueError, TypeError):
        rows = current_lvs.rows or PAGE_SIZES[settings.DEFAULT_PAGE_SIZE_IDX]
    else:
        if rows not in PAGE_SIZES:
            rows = PAGE_SIZES[settings.DEFAULT_PAGE_SIZE_IDX]

        current_lvs.rows = rows

    try:
        # TODO: rename '_search' attribute & POST param
        current_lvs._search = search = bool(int(POST_get('_search')))
    except (ValueError, TypeError):
        search = current_lvs._search or False

    ct = ContentType.objects.get_for_model(model)
    user = request.user
    header_filters = HeaderFilterList(ct, user)
    # Try first to get the posted header filter which is the most recent.
    # Then try to retrieve the header filter from session, then fallback
    hf = header_filters.select_by_id(POST_get('hfilter', -1),
                                     current_lvs.header_filter_id,
                                     hf_pk,
                                    )

    if hf is None:
        raise NoHeaderFilterAvailable()

    current_lvs.header_filter_id = hf.id

    cells = hf.cells

    if show_actions:
        cells.insert(0, EntityCellActions())

    current_lvs.handle_research(request, cells)
    # current_lvs.set_sort(model, cells,
    #                      POST_get('sort_field', current_lvs.sort_field),
    #                      POST_get('sort_order', current_lvs.sort_order),
    #                     )

    entity_filters = EntityFilterList(ct, user)
    efilter = _select_entityfilter(request, entity_filters, current_lvs.entity_filter_id)
    current_lvs.entity_filter_id = efilter.id if efilter else None

    json_q_filter, extra_filter = _build_extrafilter(request, extra_q)

    entities, count = _build_entity_queryset(request, model, current_lvs, extra_filter, efilter, hf)
    fast_mode = (count >= settings.FAST_QUERY_MODE_THRESHOLD)
    ordering = current_lvs.set_sort(model, cells,
                                    cell_key=POST_get('sort_field', current_lvs.sort_field),
                                    order=POST_get('sort_order', current_lvs.sort_order),
                                    fast_mode=fast_mode,
                                   )

    # entities_page = _build_entities_page(request, current_lvs, entities, rows, count)
    entities_page = _build_entities_page(request, current_lvs, entities.order_by(*ordering),
                                         size=rows, count=count, ordering=ordering, fast_mode=fast_mode,
                                        )

    current_lvs.register_in_session(request)

    template_dict = {
        'model':              model,
        'list_title':         _(u"List of %s") % unicode(model._meta.verbose_name_plural),
        'sub_title':          '',
        'header_filters':     header_filters,
        'entity_filters':     entity_filters,
        'entities':           entities_page,
        'list_view_state':    current_lvs,
        'content_type':       ct,
        'content_type_id':    ct.id,
        'search':             search,
        'content_template':   content_template,
        'page_sizes':         PAGE_SIZES,
        'o2m':                o2m,
        'add_url':            model.get_create_absolute_url(),
        'extra_bt_templates': None,  # TODO: () instead ???,
        'show_actions':       show_actions,
        'q_filter':           json_q_filter,
        'research_cellkeys':  {cell_key for cell_key, value in current_lvs.research},
        'is_popup_view':      False,
    }

    if extra_dict:
        template_dict.update(extra_dict)

    if request.GET.get('ajax', False):  # TODO: request.is_ajax() ?
        template = template_dict['content_template']

    if post_process:
        post_process(template_dict, request)

    # Optimisation time !!
    # hf.populate_entities(entities_page.object_list)
    hf.populate_entities(entities_page.object_list, user)

    return template, template_dict


def list_view(request, model, *args, **kwargs):
    """See list_view_content() for arguments"""
    try:
        template_name, template_dict = list_view_content(request, model, *args, **kwargs)
    except NoHeaderFilterAvailable:
        from creme.creme_core.views.header_filter import add as add_header_filter
        return add_header_filter(request, ContentType.objects.get_for_model(model).id,
                                 {'help_message': _(u"The desired list does not have any view, please create one.")}
                                )

    return render(request, template_name, template_dict)


def list_view_popup_from_widget(request, ct_id, o2m, **kwargs):
    """@param kwargs See list_view_content()"""
    ct = get_ct_or_404(ct_id)

    if not request.user.has_perm(ct.app_label):
        raise Http404(_(u"You are not allowed to access to this app"))

    req_get = lambda k, default=None: request.POST.get(k, default) or request.GET.get(k, default)
    o2m = bool(int(o2m))
    kwargs['show_actions'] = bool(int(req_get('sa', False)))
    extra_dict = {
                  'js_handler':    req_get('js_handler'),
                  'js_arguments':  req_get('js_arguments'),
                  'whoami':        req_get('whoami'),
                  'is_popup_view': True,
                 }

    extra_dict.update(kwargs.pop('extra_dict', None) or {})

    extra_q = kwargs.pop('extra_q', None)

    try:
        template_name, template_dict = list_view_content(request, ct.model_class(), extra_dict=extra_dict,
                                                         template='creme_core/frags/list_view.html',
                                                         extra_q=extra_q, o2m=o2m,
                                                         **kwargs
                                                        )
    except NoHeaderFilterAvailable:
        # TODO: true HeaderFilter creation in inner popup
        return inner_popup(request, '', {}, is_valid=False,
                           html=_(u"The desired list does not have any view, please create one.")
                          )

    return inner_popup(request, template_name, template_dict, is_valid=False)
