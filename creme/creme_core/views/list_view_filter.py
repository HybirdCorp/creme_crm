# -*- coding: utf-8 -*-

from django.db.models.query_utils import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType

from creme_core.models import Filter
from creme_core.forms.list_view_filter import ListViewFilterForm
from creme_core.entities_access.functions_for_permissions import add_view_or_die, edit_object_or_die, delete_object_or_die
from creme_core.views.generic import list_view_popup, list_view_popup_from_widget


@login_required
@add_view_or_die(ContentType.objects.get_for_model(Filter), app_name="all_creme_apps")
def add(request, ct_id):
    if request.POST:
        #beware: we doesn't test the form validity voluntarily
        filterform = ListViewFilterForm(request.POST, initial={'user': request.user.id, 'content_type_id': ct_id})
        filterform.save()
        return HttpResponseRedirect(ContentType.objects.get_for_id(ct_id).model_class().get_lv_absolute_url())

    filterform = ListViewFilterForm(initial={'user': request.user.id, 'content_type_id': ct_id})

    return render_to_response('creme_core/filters.html',
                              {'form': filterform, 'mode': 'add', 'content_type_id': ct_id},
                              context_instance=RequestContext(request))

@login_required
def get_list_view_popup_from_ct(request, content_type_id):
    return list_view_popup_from_widget(request, content_type_id, True) #call directly from urls.py ???

@login_required
def register_in_session(request, filter_id, ct_id):
    session = request.session

    if session.__contains__('filters'): #TODO: why not 'in' or get(), or better: pop() ????
        filters = session.get('filters')
        if filters.has_key(str(ct_id)):
            filters[str(ct_id)] = filter_id
        else:
            filters.update({ct_id: filter_id}) #why not 'filters[ct_id] = filter_id' ??
        del session['filters'] #useful ???
    else:
        filters = {ct_id : filter_id}

    session.__setitem__('filters', filters) #why not session['filters'] = filters ????

    return HttpResponse('', mimetype="text/javascript")

@login_required
def get_session_filter_id(request, ct_id):
    filters = request.session.get('filters')
    filter_id = ""

    if filters:
        filter_id = filters.get(str(ct_id), filter_id)

    return HttpResponse(filter_id)

@login_required
def delete(request, filter_id):
    filter_ = get_object_or_404(Filter, pk=filter_id)
    ct_id = filter_.model_ct_id

    die_status = delete_object_or_die(request, filter_)
    if die_status:
        return die_status

    filter_.delete()

    return HttpResponseRedirect(ContentType.objects.get_for_id(ct_id).model_class().get_lv_absolute_url())

#TODO: s/champ/field !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
@login_required
def edit(request, ct_id, filter_id):
    try:
        filter_id = int(filter_id)
        ct_id = int(ct_id)
    except ValueError:
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    current_filter = get_object_or_404(Filter, pk=filter_id)
    model_klass = ContentType.objects.get_for_id(ct_id).model_class()

    die_status = edit_object_or_die(request, current_filter)
    if die_status:
        return die_status

    if request.POST :
        filterform = ListViewFilterForm(request.POST, initial={'user': request.user.id, 'content_type_id': ct_id, 'filter_id': filter_id})
        filterform.save()
        return HttpResponseRedirect(model_klass.get_lv_absolute_url())

    filterform = ListViewFilterForm(initial={'user': request.user.id, 'content_type_id': ct_id})
    filterform.fields['nom'].initial = current_filter.name

    edit_dict_condition = []

    model_klass_has_attr = hasattr(model_klass, 'extra_filter_fields')

    for condition in current_filter.conditions.filter(~Q(champ__contains='relations') & ~Q(champ__contains='properties')):
        text_values = ",".join([value.value for value in condition.values.all()])

        if model_klass_has_attr and condition.champ in (f['name'] for f in model_klass.extra_filter_fields):
            champ = condition.champ
            champ_fk = ""
        else:
            champs = condition.champ.split('__') #TODO: can be improved with: champ, sep, champ_fk = condition.champ.partition('__') ???
            if len(champs) == 1:
                champ = champs[0]
                champ_fk = ""
            elif len(champs) > 1:
                champ = champs[0]
                champ_fk = champs[1]
            else:
                champ = ""
                champ_fk = ""
        edit_dict_condition.append({'champ': champ, 'champ_fk': champ_fk, 'test': condition.type.pk, 'value': text_values})

    edit_dict = {'condition':     edit_dict_condition,
                 'filter':        [pfilter.pk for pfilter in current_filter.parent_filters.all()],
                 'is_or_for_all': current_filter.is_or_for_all,
                }

    rel_conditions = []
    for condition in current_filter.conditions.filter(Q(champ__contains='relations')):
        dict_conditions = {
            'predicate_id':  condition.values.all(),
            'has_predicate': int(condition.type.is_exclude),
            'is_child':      bool(condition.child_type)
        }

        try:
            get_children = condition.childs.filter
            dict_conditions.update(
                content_type_id=get_children(child_type__type="content_type")[0].values.all()[0],
                object_id=get_children(child_type__type="object_id")[0].values.all()[0],
            )
        except IndexError:
            dict_conditions.update(content_type_id=None, object_id=None)

        rel_conditions.append(dict_conditions)


    prop_conditions = [{'property_id': condition.values.all(), 'has_property': int(condition.type.is_exclude)}
                            for condition in current_filter.conditions.filter(champ__contains='properties')
                      ]

    return render_to_response('creme_core/filters.html',
                              {'form': filterform,
                               'mode': 'edit',
                               'edit_dict': edit_dict,
                               'content_type_id': ct_id,
                               'relations_conditions': rel_conditions,
                               'properties_conditions': prop_conditions
                              },
                              context_instance=RequestContext(request))
