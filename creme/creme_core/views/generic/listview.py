# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from itertools import chain
from json import loads as json_load, dumps as json_dump

import logging
import warnings

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.db.models.query_utils import Q
from django.http import HttpResponse
from django.shortcuts import render
from django.template import Template, Context
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.core.entity_cell import EntityCellActions
from creme.creme_core.core.paginator import FlowPaginator, LastPage
from creme.creme_core.gui.actions import actions_registry
from creme.creme_core.gui.listview import ListViewState, NoHeaderFilterAvailable
from creme.creme_core.models import CremeEntity
from creme.creme_core.models.entity_filter import EntityFilterList
from creme.creme_core.models.header_filter import HeaderFilterList
from creme.creme_core.utils import get_from_POST_or_404, get_from_GET_or_404
from creme.creme_core.utils.queries import get_q_from_dict, QSerializer

logger = logging.getLogger(__name__)

# MODE_NORMAL = 0  # TODO ? (no selection)
MODE_SINGLE_SELECTION = 1
MODE_MULTIPLE_SELECTION = 2


def str_to_mode(value):
    """Convert a string to list-view mode.
    Useful to convert a GET parameter.
    """
    if value == 'single':
        return MODE_SINGLE_SELECTION

    if value == 'multiple':
        return MODE_MULTIPLE_SELECTION

    raise ValueError('Must be "single" or "multiple"')


def _clean_value(value, converter, default=None):
    warnings.warn('creme_core.views.generic.listview._clean_value() is deprecated.',
                  DeprecationWarning
                 )

    try:
        return converter(value)
    except Exception as e:
        if default is not None:
            return default

        raise e


def _build_entity_queryset(user, model, list_view_state, extra_q, entity_filter, header_filter):
    filtered = False
    use_distinct = False
    queryset = model.objects.filter(is_deleted=False)

    if entity_filter:
        filtered = True
        queryset = entity_filter.filter(queryset)

    if extra_q:
        try:
            queryset = queryset.filter(extra_q)
        except Exception as e:
            logger.exception('Error when building the search queryset: invalid q_filter (%s).', e)
        else:
            filtered = True
            use_distinct = True

    list_view_state.extra_q = extra_q   # TODO: only if valid ?

    # TODO: method in ListViewState that returns the improved queryset
    lv_state_q = list_view_state.get_q_with_research(model, header_filter.cells)
    try:
        queryset = queryset.filter(lv_state_q)
    except Exception as e:
        logger.exception('Error when building the search queryset with Q=%s (%s).', lv_state_q, e)
    else:
        if lv_state_q:
            filtered = True
            use_distinct = True

    queryset = EntityCredentials.filter(user, queryset)

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

    return queryset, count


def _build_entities_page(arguments, list_view_state, queryset, size, count, ordering, fast_mode=False):
    if not fast_mode:
        paginator = Paginator(queryset, size)
        paginator.count = count

        try:
            page = int(arguments['page'])
        except (KeyError, ValueError, TypeError):
            page = list_view_state.page or 1

        try:
            entities_page = paginator.page(page)
        except (EmptyPage, InvalidPage):
            entities_page = paginator.page(paginator.num_pages)

        list_view_state.page = entities_page.number
    else:
        paginator = FlowPaginator(queryset=queryset, key=ordering[0], per_page=size, count=count)
        page_str = arguments.get('page') or str(list_view_state.page)

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

        list_view_state.page = json_dump(entities_page.info(), separators=(',', ':'))

    return entities_page


def _build_extrafilter(arguments, extra_filter=None):
    json_q_filter = arguments.get('q_filter')
    q_filter = Q()
    serializer = QSerializer()

    # TODO: better validation of q_filter ? (corresponding EntityCell allowed + searchable ?)
    #  - limit the max depth of sub-fields chain ?
    #  - do no allow all fields ?
    if json_q_filter:
        try:
            q_filter = serializer.loads(json_q_filter)
        except:
            try:
                q_filter = get_q_from_dict(_clean_value(json_q_filter, json_load, {}))
            except:
                raise
            else:
                warnings.warn('Old format for "q_filter" is deprecated is used : {}'.format(json_q_filter),
                              DeprecationWarning
                             )

    return (serializer.dumps(q_filter),
            q_filter if extra_filter is None else q_filter & extra_filter
           )


def _select_entityfilter(arguments, entity_filters, default_filter):
    efilter_id = arguments.get('filter', default_filter)
    return entity_filters.select_by_id(efilter_id)


def _build_rowscount(arguments, list_view_state):
    PAGE_SIZES = settings.PAGE_SIZES

    try:
        rows = int(arguments.get('rows'))
    except (ValueError, TypeError):
        rows = list_view_state.rows or PAGE_SIZES[settings.DEFAULT_PAGE_SIZE_IDX]
    else:
        if rows not in PAGE_SIZES:
            rows = PAGE_SIZES[settings.DEFAULT_PAGE_SIZE_IDX]

        list_view_state.rows = rows

    return rows


# TODO: use mode=MODE_* instead of "o2m"
def list_view_content(request, model, hf_pk='', extra_dict=None,
                      template='creme_core/generics/list_entities.html',
                      show_actions=True, extra_q=None, mode=MODE_MULTIPLE_SELECTION, post_process=None,
                      content_template='creme_core/frags/list_view_content.html',
                      lv_state_id=None
                     ):
    """ Generic list_view wrapper / generator
    Accepts only CremeEntity model and subclasses.
    @param post_process: Function that takes the template context and the
                         request as parameters (so you can modify the context).
    """
    assert issubclass(model, CremeEntity), '{} is not a subclass of CremeEntity'.format(model)

    PAGE_SIZES = settings.PAGE_SIZES

    is_GET = request.method == 'GET'
    arguments = request.GET if is_GET else request.POST
    lv_state_id = lv_state_id or request.path
    current_lvs = ListViewState.get_or_create_state(request, url=lv_state_id)

    rows = _build_rowscount(arguments, current_lvs)

    transient = is_GET or (arguments.get('transient') in {'1', 'true'})
    ct = ContentType.objects.get_for_model(model)
    user = request.user
    header_filters = HeaderFilterList(ct, user)

    hf = current_lvs.set_headerfilter(header_filters, arguments.get('hfilter', -1), hf_pk)
    cells = hf.cells

    if show_actions:
        cells.insert(0, EntityCellActions(model=model, actions_registry=actions_registry))

    if arguments.get('search', '') == 'clear':
        current_lvs.clear_research()
    else:
        current_lvs.handle_research(arguments, cells, merge=transient)

    entity_filters = EntityFilterList(ct, user)
    efilter = _select_entityfilter(arguments, entity_filters, current_lvs.entity_filter_id)
    current_lvs.entity_filter_id = efilter.id if efilter else None

    json_q_filter, extra_filter = _build_extrafilter(arguments, extra_q)

    entities, count = _build_entity_queryset(user, model, current_lvs, extra_filter, efilter, hf)
    fast_mode = (count >= settings.FAST_QUERY_MODE_THRESHOLD)
    ordering = current_lvs.set_sort(model, cells,
                                    cell_key=arguments.get('sort_field', current_lvs.sort_field),
                                    order=arguments.get('sort_order', current_lvs.sort_order),
                                    fast_mode=fast_mode,
                                   )

    entities_page = _build_entities_page(arguments, current_lvs, entities.order_by(*ordering),
                                         size=rows, count=count, ordering=ordering, fast_mode=fast_mode,
                                        )

    if not transient:
        current_lvs.register_in_session(request)

    template_dict = {
        'model':              model,
        'list_title':         _('List of {models}').format(models=model._meta.verbose_name_plural),
        'sub_title':          '',
        'header_filters':     header_filters,
        'entity_filters':     entity_filters,
        'entities':           entities_page,
        'list_view_state':    current_lvs,
        'content_type':       ct,
        'content_type_id':    ct.id,
        'search':             len(current_lvs.research) > 0,
        'content_template':   content_template,
        'page_sizes':         PAGE_SIZES,
        'o2m':                (mode == MODE_SINGLE_SELECTION),
        'add_url':            model.get_create_absolute_url(),
        'extra_bt_templates': None,  # TODO: () instead ???,
        'show_actions':       show_actions,
        'extra_filter':       QSerializer().dumps(extra_filter),
        'q_filter':           json_q_filter,
        'research_cellkeys':  {cell_key for cell_key, _value in current_lvs.research},
        'is_popup_view':      False,
    }

    if extra_dict:
        template_dict.update(extra_dict)

    if request.is_ajax():
        template = template_dict['content_template']

    if post_process:
        post_process(template_dict, request)

    # Optimisation time !!
    hf.populate_entities(entities_page.object_list, user)

    return template, template_dict


def list_view(request, model, **kwargs):
    """See list_view_content() for arguments"""

    if request.method == 'POST':
        mode = get_from_POST_or_404(request.POST, 'selection', cast=str_to_mode, default='multiple')
    else:
        mode = get_from_GET_or_404(request.GET, 'selection', cast=str_to_mode, default='multiple')

    try:
        template_name, template_dict = list_view_content(request, model, mode=mode, **kwargs)
    except NoHeaderFilterAvailable:
        from ..header_filter import HeaderFilterCreation

        logger.critical('No HeaderFilter is available for <%s> ; '
                        'the developer should have created one in "populate.py" script',
                        model
                       )

        class EmergencyHeaderFilterCreation(HeaderFilterCreation):
            def get_context_data(self, **kwargs):
                context = super().get_context_data(**kwargs)
                context['help_message'] = _('The desired list does not have any view, please create one.')

                return context

            def get_success_url(self):
                return self.request.path

        return EmergencyHeaderFilterCreation.as_view()(request, ct_id=ContentType.objects.get_for_model(model).id)

    return render(request, template_name, template_dict)


# NB: will be removed in Creme 2.1 (so do not use it...)
__inner_popup = Template(
"""<div class="in-popup" force-reload>
    <div id="inner_header" style="display: none;">
        <input name="inner_header_from_url" value="{{from_url}}" type="hidden"/>
    </div>
    <div name="inner_body">
        <input type="hidden" name="whoami" value="{{whoami}}"/>
        {% for persist_key, persist_values in persisted.items %}
            {% for persist_value in persist_values %}
                <input type="hidden" name="{{persist_key}}" value="{{persist_value}}"/>
                <input type="hidden" name="persist" value="{{persist_key}}"/>
            {% endfor %}
        {% endfor %}
        {{html}}
    </div>
</div>
""")


# TODO: add a no-selection mode ??
def list_view_popup(request, model, mode=MODE_SINGLE_SELECTION, lv_state_id=None, **kwargs):
    """ Displays a list-view selector in an inner popup.
    @param model: Class inheriting CremeEntity.
    @param mode: Selection mode, in (MODE_SINGLE_SELECTION, MODE_MULTIPLE_SELECTION).
    @param kwargs: See list_view_content().
    """
    assert mode in (MODE_SINGLE_SELECTION, MODE_MULTIPLE_SELECTION)

    request.user.has_perm_to_access_or_die(model._meta.app_label)

    # TODO: only use GET on GET request etc...

    # NB: we have duplicated the code of popup.inner_popup() in order to deprecate it without having
    #     some annoying deprecation messages. This function will probably be removed in Creme 2.1
    #     because of the big rework of the list-view code (class-based views, ...)

    GET = request.GET
    POST = request.POST
    kwargs['show_actions'] = bool(int(GET.get('sa', False)))
    whoami = POST.get('whoami') or GET.get('whoami')
    extra_dict = {
        'whoami':        whoami,
        'is_popup_view': True,
    }
    tpl_persist = {
        persist_key: POST.getlist(persist_key) + GET.getlist(persist_key)
            for persist_key in chain(POST.getlist('persist'),
                                     GET.getlist('persist'),
                                    )
    }

    extra_dict.update(kwargs.pop('extra_dict', None) or {})

    extra_q = kwargs.pop('extra_q', None)

    try:
        template_name, template_dict = list_view_content(
            request, model=model, extra_dict=extra_dict,
            # TODO: rename list-view-popup.html
            template='creme_core/frags/list_view.html',
            extra_q=extra_q,
            mode=mode,
            lv_state_id=lv_state_id,
            **kwargs
        )
    except NoHeaderFilterAvailable:
        # TODO: true HeaderFilter creation in inner popup
        html = _('The desired list does not have any view, please create one.')
    else:
        template_dict['persisted'] = tpl_persist
        template_dict['is_inner_popup'] = True
        html = render_to_string(template_name, template_dict, request=request)

    return HttpResponse(
        __inner_popup.render(Context({
            'html':      html,
            'from_url':  request.path,
            'whoami':    whoami,
            'persisted': tpl_persist,
        })),
        content_type='text/html',
    )
