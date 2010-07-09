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
import csv

from django.http import HttpResponse
from django.db import models
from django.db.models.fields import FieldDoesNotExist
from django.db.models import Q
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.shortcuts import render_to_response, get_object_or_404
from django.template.context import RequestContext
from django.utils.simplejson import JSONDecoder
from django.utils.encoding import smart_str
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeEntity, Filter, ListViewState, CustomFieldValue
from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD, HFI_RELATION, HFI_FUNCTION, HFI_CUSTOM
from creme_core.gui.last_viewed import change_page_for_last_item_viewed
from creme_core.entities_access.permissions import user_has_create_permission
from creme_core.entities_access.filter_allowed_objects import filter_RUD_objects
from creme_core.utils.meta import get_field_infos
from popup import inner_popup


_hfi_action = HeaderFilterItem(order=0, name='entity_actions', title='Actions', has_a_filter=False, editable=False, is_hidden=False)

def _get_header_filter(request, content_type, list_view_state, fallback_header_filter_id):
    try:
        #Try to retrieve header filter from session
        hf = HeaderFilter.objects.get(pk=list_view_state.header_filter_id)
    except HeaderFilter.DoesNotExist:
        try:
            #Try to retrieve header filter from filter name parameter
            hf = HeaderFilter.objects.get(pk=fallback_header_filter_id, entity_type=content_type) #'entity_type=content_type' useful ???
        except HeaderFilter.DoesNotExist:
            try:
                #Try to retrieve header filter from a list of header filters for this content type
                hf = HeaderFilter.objects.filter(entity_type=content_type)[0]
            except IndexError:
                return None #No one is available

    #Get the posted header filter which is the most recent
    new_hf_id = request.POST.get('hfilter')

    if new_hf_id and new_hf_id != hf.id:
        try:
            hf = HeaderFilter.objects.get(pk=new_hf_id)
        except HeaderFilter.DoesNotExist:
            pass

    list_view_state.header_filter_id = hf.id

    return hf

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
    queryset = filter_RUD_objects(request, queryset).distinct().order_by("%s%s" % (list_view_state.sort_order, list_view_state.sort_field))

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
def list_view(request, model, hf_pk='', extra_dict=None, template='creme_core/generics/list_entities.html', show_actions=True, extra_q=None, o2m=False):
    """
        Generic list_view wrapper / generator
        Accept only CremeEntity model and subclasses
        @Permissions : Filter RUD objects
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

    hf = _get_header_filter(request, ct, current_lvs, hf_pk)
    if hf is None:
        from creme_core.views.header_filter import add as add_header_filter
        return add_header_filter(request, ct.id, {'help_message': u"La liste souhaitée n'a aucune vue, veuillez en créer au moins une."})

    hfi = HeaderFilterItem.objects.filter(header_filter=hf).order_by('order')
    current_lvs.handle_research(request, hfi)

    if show_actions:
        hfi = list(hfi)
        hfi.insert(0, _hfi_action)

    #TODO: in a method ListViewState.init_sort_n_field() ???
    try:
        default_model_ordering = model._meta.ordering[0]
    except IndexError:
        default_model_ordering = 'id'

    current_lvs.sort_field = POST_get('sort_field', current_lvs.sort_field or default_model_ordering)
    current_lvs.sort_order = POST_get('sort_order', current_lvs.sort_order or '')

    entities = _build_entities_page(request, current_lvs, _build_entity_queryset(request, model, current_lvs, extra_q), rows)

    current_lvs.register_in_session(request)

    template_dict = {
        'model':              model,
        'list_title':         u"Liste des %s" % unicode(model._meta.verbose_name_plural),
        'columns':            hfi,
        'entities':           entities,
        'list_view_state':    current_lvs,
        'content_type_id':    ct.id,
        'filter_id' :         current_lvs.filter_id or '',
        'hfilter_id':         hf.id,
        'search':             _search,
        'list_view_template': 'creme_core/frags/list_view.html',
        'o2m':                o2m,
        'add_url':            None,
        'extra_bt_templates': None, # () instead ???
    }

    if extra_dict:
        template_dict.update(extra_dict)

    if request.GET.get('ajax', False):
        template = 'creme_core/frags/list_view_content.html'

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
    extra_q = Q(**JSONDecoder().decode(str(req_get('q_filter', {}))) or {})

    #TODO: Can be improved ?
    supplied_extra_q = kwargs.pop('extra_q', None)
    if supplied_extra_q:
        extra_q &= supplied_extra_q

    response = list_view_popup(request, model, extra_dict=extra_dict, o2m=o2m, extra_q=extra_q, *args, **kwargs)

    return inner_popup(request, '', {}, is_valid=False, html=response._get_content(), context_instance=RequestContext(request))


#TODO: optimise queries (with caches)
@login_required
def dl_listview_as_csv(request, ct_id):
    ct    = get_object_or_404(ContentType, pk=ct_id)
    model = ct.model_class()

    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename="%s.csv"' % ct.model

    #TODO: is it possible that session doesn't content the state (eg: url linked and open directly) ????
    current_lvs = ListViewState.get_state(request, url=request.GET['list_url'])

    #TODO: factorise (with list_view()) ?? in a ListViewState's method ???
    columns = HeaderFilterItem.objects.filter(header_filter__id=current_lvs.header_filter_id).order_by('order')
    current_lvs.handle_research(request, columns)

    sort_order = current_lvs.sort_order or ''
    sort_field = current_lvs.sort_field

    if not sort_field:
        try:  #'if model._meta.ordering' instead ????
            sort_field = model._meta.ordering[0]
        except IndexError:
            sort_field = 'id'

    q_is_deleted = Q(is_deleted=False) | Q(is_deleted=None)

    if current_lvs.filter_id:
        filter_ = Filter.objects.get(pk=current_lvs.filter_id)
        entities = model.objects.filter(q_is_deleted & filter_.get_q())
    else:
        entities = model.objects.filter(q_is_deleted)

    if current_lvs.extra_q:
        entities = entities.filter(current_lvs.extra_q)

    entities = entities.filter(current_lvs.get_q_with_research(model))
    entities = filter_RUD_objects(request, entities).distinct().order_by("%s%s" % (sort_order, sort_field))

    #TODO: move to a template ???
    writer = csv.writer(response, delimiter=";")
    writerow = writer.writerow

    writerow([smart_str(column.title) for column in columns]) #doesn't accept generator expression... ;(

    for entity in entities:
        line = []

        for column in columns:
            #move to a HeaderFilterItem method ?????? (problen with relation --> several objects returned)
            try:
                type_ = column.type

                if type_ == HFI_FIELD:
                    res = smart_str(get_field_infos(entity, column.name)[1])
                elif type_ == HFI_FUNCTION:
                    res = smart_str(getattr(entity, column.name)())
                elif type_ == HFI_RELATION:
                    res = smart_str(u'/'.join(unicode(o) for o in entity.get_list_object_of_specific_relations(column.relation_predicat_id)))
                else:
                    assert type_ == HFI_CUSTOM
                    res = smart_str(CustomFieldValue.get_pretty_value(column.name, entity.id))
            except Exception, e:
                debug('Exception in CSV export: %s', e)
                res = ''

            line.append(res)

        writerow(line)

    return response
