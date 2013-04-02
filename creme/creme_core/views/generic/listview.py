# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from django.db.models import Q
from django.http import Http404
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.shortcuts import render
from django.utils.simplejson import JSONDecoder
from django.utils.translation import ugettext as _
from django.contrib.contenttypes.models import ContentType

from creme.creme_core.models import CremeEntity, EntityCredentials
from creme.creme_core.models.header_filter import HeaderFilterList
from creme.creme_core.models.entity_filter import EntityFilterList
from creme.creme_core.gui.listview import ListViewState
from creme.creme_core.views.header_filter import add as add_header_filter
from creme.creme_core.utils import get_ct_or_404
from creme.creme_core.utils.queries import get_q_from_dict
from .popup import inner_popup


class NoHeaderFilterAvailable(Exception):
    pass


def _build_entity_queryset(request, model, list_view_state, extra_q, entity_filter):
    queryset = model.objects.filter(is_deleted=False)

    if entity_filter:
        queryset = entity_filter.filter(queryset)

    if extra_q:
        queryset = queryset.filter(extra_q)

    list_view_state.extra_q = extra_q
    queryset = queryset.filter(list_view_state.get_q_with_research(model))

    return EntityCredentials.filter(request.user, queryset) \
                            .distinct() \
                            .order_by("%s%s" % (list_view_state.sort_order, list_view_state.sort_field))

def _build_entities_page(request, list_view_state, queryset, size):
    paginator = Paginator(queryset, size)

    try:
        page = int(request.POST.get('page'))
        list_view_state.page = page
    except (ValueError, TypeError):
        page = list_view_state.page or 1

    try:
        entities_page = paginator.page(page)
    except (EmptyPage, InvalidPage):
        entities_page = paginator.page(paginator.num_pages)

    return entities_page

def list_view_content(request, model, hf_pk='', extra_dict=None, template='creme_core/generics/list_entities.html',
                      show_actions=True, extra_q=None, o2m=False, post_process=None,
                     ):
    """ Generic list_view wrapper / generator
    Accept only CremeEntity model and subclasses
    @param post_process Function that takes the template context and the request as parameters (so you can modify the context).
    """
    assert issubclass(model, CremeEntity), '%s is not a subclass of CremeEntity' % model

    POST_get = request.POST.get

    current_lvs = ListViewState.get_state(request)
    if current_lvs is None:
        current_lvs = ListViewState.build_from_request(request) #TODO: move to ListViewState.get_state() ???

    try:
        rows = int(POST_get('rows'))
        current_lvs.rows = rows
    except (ValueError, TypeError):
        rows = current_lvs.rows or 25

    try:
        _search = bool(int(POST_get('_search')))
        current_lvs._search = _search
    except (ValueError, TypeError):
        _search = current_lvs._search or False

    ct = ContentType.objects.get_for_model(model)
    header_filters = HeaderFilterList(ct)
    #Try first to get the posted header filter which is the most recent.
    #Then try to retrieve the header filter from session, then fallback
    hf = header_filters.select_by_id(POST_get('hfilter', -1), current_lvs.header_filter_id, hf_pk)

    if hf is None:
        raise NoHeaderFilterAvailable()

    current_lvs.header_filter_id = hf.id

    hf.build_items(show_actions)
    current_lvs.handle_research(request, hf.items)

    #TODO: in a method ListViewState.init_sort_n_field() ???
    try:
        default_model_ordering = model._meta.ordering[0]
    except IndexError:
        default_model_ordering = 'id'

    current_lvs.sort_field = POST_get('sort_field', current_lvs.sort_field or default_model_ordering)
    current_lvs.sort_order = POST_get('sort_order', current_lvs.sort_order or '')

    entity_filters = EntityFilterList(ct)
    efilter = entity_filters.select_by_id(POST_get('filter', current_lvs.entity_filter_id))
    current_lvs.entity_filter_id = efilter.id if efilter else None

    entities = _build_entity_queryset(request, model, current_lvs, extra_q, efilter)
    entities = _build_entities_page(request, current_lvs, entities, rows)

    current_lvs.register_in_session(request)

    template_dict = {
        'model':              model,
        'list_title':         _(u"List of %s") % unicode(model._meta.verbose_name_plural),
        'sub_title':          '',
        'header_filters':     header_filters,
        'entity_filters':     entity_filters,
        'entities':           entities,
        'list_view_state':    current_lvs,
        'content_type_id':    ct.id,
        'search':             _search,
        'list_view_template': 'creme_core/frags/list_view.html',
        'o2m':                o2m,
        'add_url':            None,
        'extra_bt_templates': None, # () instead ???,
        'show_actions':       show_actions,
        'current_research_fields': [str(name_attribut) for (name_attribut, pk, type, pattern, value) in current_lvs.research],
    }

    if extra_dict:
        template_dict.update(extra_dict)

    if request.GET.get('ajax', False):
        template = 'creme_core/frags/list_view_content.html'

    if post_process:
        post_process(template_dict, request)

    #optimisation time !!
    hf.populate_entities(entities.object_list, request.user)

    return template, template_dict

def list_view(request, model, *args, **kwargs):
    """See list_view_content() for arguments"""
    try:
        template_name, template_dict = list_view_content(request, model, *args, **kwargs)
    except NoHeaderFilterAvailable:
        return add_header_filter(request, ContentType.objects.get_for_model(model).id,
                                 {'help_message': _(u"The desired list does not have any view, please create one.")}
                                )

    return render(request, template_name, template_dict)

def list_view_popup_from_widget(request, ct_id, o2m, **kwargs):
    """@param kwargs See list_view_content()"""
    ct = get_ct_or_404(ct_id)

    if not request.user.has_perm(ct.app_label):
        raise Http404(_(u"You are not allowed to acceed to this app"))

    req_get = request.REQUEST.get
    o2m = bool(int(o2m))

    json_str_q_filter = str(req_get('q_filter', {}))
    kwargs['show_actions'] = bool(int(req_get('sa', False)))

    extra_dict = {'list_view_template': 'creme_core/frags/list_view_popup.html',
                  'js_handler':         req_get('js_handler'),
                  'js_arguments':       req_get('js_arguments'),
                  'whoami':             req_get('whoami'),
                  'q_filter':           json_str_q_filter,
                  'is_popup_view':      True,
                 }

    extra_dict.update(kwargs.pop('extra_dict', None) or {})

    extra_q = get_q_from_dict(JSONDecoder().decode(json_str_q_filter) or {})

    supplied_extra_q = kwargs.pop('extra_q', None)
    if supplied_extra_q:
        extra_q &= supplied_extra_q

    try:
        template_name, template_dict = list_view_content(request, ct.model_class(), extra_dict=extra_dict,
                                                         template='creme_core/generics/list_entities_popup.html',
                                                         extra_q=extra_q, o2m=o2m,
                                                         **kwargs
                                                        )
    except NoHeaderFilterAvailable:
        #TODO: true HeaderFilter creation in inner popup
        return inner_popup(request, '', {}, is_valid=False,
                           html=_(u"The desired list does not have any view, please create one.")
                          )

    return inner_popup(request, template_name, template_dict, is_valid=False)
