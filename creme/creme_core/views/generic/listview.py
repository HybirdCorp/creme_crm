# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from logging import debug

from django.db.models import Q
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.shortcuts import render_to_response, get_object_or_404
from django.template.context import RequestContext
from django.utils.simplejson import JSONDecoder
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeEntity, Filter, ListViewState, EntityCredentials
from creme_core.models.header_filter import HeaderFilterList
from creme_core.gui.last_viewed import change_page_for_last_item_viewed
from creme_core.utils.queries import get_q_from_dict
from popup import inner_popup


def _build_entity_queryset(request, model, list_view_state, extra_q):
    query = Q(is_deleted=False) | Q(is_deleted=None)

    try:
        filter_ = Filter.objects.get(pk=int(request.POST.get('filter', list_view_state.filter_id or '')))
    except (Filter.DoesNotExist, ValueError), e:
        list_view_state.filter_id = None
    else:
        list_view_state.filter_id = filter_.id
        query &= filter_.get_q()

    queryset = model.objects.filter(query)

    if extra_q:
        queryset = queryset.filter(extra_q)
    list_view_state.extra_q = extra_q

    queryset = queryset.filter(list_view_state.get_q_with_research(model))
    queryset = EntityCredentials.filter(request.user, queryset)
    queryset = queryset.distinct().order_by("%s%s" % (list_view_state.sort_order, list_view_state.sort_field))

    return queryset

def _build_entities_page(request, list_view_state, queryset, size):
    paginator = Paginator(queryset, size)

    try:
        page = int(request.POST.get('page'))
        list_view_state.page = page
    except (ValueError, TypeError), error:
        page = list_view_state.page or 1

    try:
        entities_page = paginator.page(page)
    except (EmptyPage, InvalidPage), e:
        entities_page = paginator.page(paginator.num_pages)

    return entities_page

@login_required
@change_page_for_last_item_viewed
def list_view(request, model, hf_pk='', extra_dict=None, template='creme_core/generics/list_entities.html', show_actions=True, extra_q=None, o2m=False, post_process=None):
    """ Generic list_view wrapper / generator
    Accept only CremeEntity model and subclasses
    @param post_process Function that takes the template context as parameter (so you can modify it).
    """
    assert issubclass(model, CremeEntity), '%s is not a subclass of CremeEntity' % model

    POST_get = request.POST.get

    current_lvs = ListViewState.get_state(request)
    if current_lvs is None:
        current_lvs = ListViewState.build_from_request(request) #TODO: move to ListViewState.get_state() ???

    try:
        rows = int(POST_get('rows'))
        current_lvs.rows = rows
    except (ValueError, TypeError), error:
        rows = current_lvs.rows or 25

    try:
        _search = bool(int(POST_get('_search')))
        current_lvs._search = _search
    except (ValueError, TypeError), error:
        _search = current_lvs._search or True

    ct = ContentType.objects.get_for_model(model)
    header_filters = HeaderFilterList(ct)
    #Try first to get the posted header filter which is the most recent.
    #Then try to retrieve the header filter from session, then fallback
    hf = header_filters.select_by_id(POST_get('hfilter', -1), current_lvs.header_filter_id, hf_pk)

    if hf is None:
        from creme_core.views.header_filter import add as add_header_filter
        return add_header_filter(request, ct.id, {'help_message': _(u"The desired list does not have any view, please create one.")})
    else:
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

    entities = _build_entity_queryset(request, model, current_lvs, extra_q)
    entities = hf.improve_queryset(entities) #optimisation time !!!
    entities = _build_entities_page(request, current_lvs, entities, rows)

    current_lvs.register_in_session(request)

    template_dict = {
        'model':              model,
        'list_title':         _(u"List of %s") % unicode(model._meta.verbose_name_plural),
        'header_filters':     header_filters,
        'entities':           entities,
        'list_view_state':    current_lvs,
        'content_type_id':    ct.id,
        'filter_id' :         current_lvs.filter_id or '',
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
        post_process(template_dict)

    #optimisation time !!
    hf.populate_entities(entities.object_list, request.user)

    return render_to_response(template, template_dict, context_instance=RequestContext(request))

@login_required
def list_view_popup(request, model, extra_dict=None, o2m=False, extra_q=None, *args, **kwargs):
    popup_extra_dict = {'is_popup_view': True}

    if extra_dict:
        popup_extra_dict.update(extra_dict)

    return list_view(request, model,
                     template="creme_core/generics/list_entities_popup.html",
                     show_actions=False,
                     extra_dict=popup_extra_dict,
                     o2m=o2m,
                     extra_q=extra_q,
                     *args,
                     **kwargs)

@login_required
def list_view_popup_from_widget(request, ct_id, o2m, *args, **kwargs):
    req_get = request.REQUEST.get
    o2m = bool(int(o2m))
    extra_dict = {
                    'list_view_template': 'creme_core/frags/list_view_popup.html',
                    'js_handler':         req_get('js_handler'),
                    'js_arguments':       req_get('js_arguments'),
                    'whoami':             req_get('whoami'),
                 }

    #TODO: Can be improved ?
    supplied_extra_dict = kwargs.pop('extra_dict', None)
    if supplied_extra_dict:
        extra_dict.update(supplied_extra_dict)

    model = get_object_or_404(ContentType, pk=ct_id).model_class()

    extra_q_dict = JSONDecoder().decode(str(req_get('q_filter', {}))) or {}
#    ex_q_dict = dict((str(k), v) for k, v in extra_q_dict.items())
#
#    extra_q = Q(**(ex_q_dict or {}))

    extra_q = get_q_from_dict(extra_q_dict)

    #TODO: Can be improved ?
    supplied_extra_q = kwargs.pop('extra_q', None)
    if supplied_extra_q:
        extra_q &= supplied_extra_q

    response = list_view_popup(request, model, extra_dict=extra_dict, o2m=o2m, extra_q=extra_q, *args, **kwargs)

    return inner_popup(request, '', {}, is_valid=False, html=response._get_content(), context_instance=RequestContext(request))
