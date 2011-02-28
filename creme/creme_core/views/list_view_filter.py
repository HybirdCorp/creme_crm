# -*- coding: utf-8 -*-

from django.core import serializers
from django.db.models.query_utils import Q
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType

from creme_core.populate import DATE_RANGE_FILTER
from creme_core.models import Filter
from creme_core.forms.list_view_filter import ListViewFilterForm
from creme_core.utils import get_ct_or_404, jsonify, get_from_POST_or_404
from creme_core.utils.meta import get_flds_with_fk_flds
from creme_core.views.generic import list_view_popup_from_widget


@login_required
#@add_view_or_die(ContentType.objects.get_for_model(Filter), app_name="all_creme_apps")
#TODO: @permission_required('creme_core') ??
def add(request, ct_id):
    if request.POST:
        #beware: we doesn't test the form validity voluntarily
        #filterform = ListViewFilterForm(request.POST, initial={'user': request.user.id, 'content_type_id': ct_id})
        filterform = ListViewFilterForm(request.POST, initial={'content_type_id': ct_id})
        filterform.save()
        return HttpResponseRedirect(ContentType.objects.get_for_id(ct_id).model_class().get_lv_absolute_url())

    #filterform = ListViewFilterForm(initial={'user': request.user.id, 'content_type_id': ct_id})
    filterform = ListViewFilterForm(initial={'content_type_id': ct_id})

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
def delete(request):
    lv_filter = get_object_or_404(Filter, pk=get_from_POST_or_404(request.POST, 'id'))
    ct_id = lv_filter.model_ct_id
    allowed, msg = lv_filter.can_edit_or_delete(request.user)

    if not allowed:
        raise Http404(msg)

    lv_filter.delete()

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

    allowed, msg = current_filter.can_edit_or_delete(request.user)
    if not allowed:
        raise Http404(msg)

    if request.method == 'POST':
        #filterform = ListViewFilterForm(request.POST, initial={'user': request.user.id, 'content_type_id': ct_id, 'filter_id': filter_id})
        filterform = ListViewFilterForm(request.POST, initial={'content_type_id': ct_id, 'filter_id': filter_id})
        filterform.save()
        return HttpResponseRedirect(model_klass.get_lv_absolute_url())

    #filterform = ListViewFilterForm(initial={'user': request.user.id, 'content_type_id': ct_id})
    filterform = ListViewFilterForm(initial={'content_type_id': ct_id})
    filterform.fields['nom'].initial = current_filter.name
    filterform.fields['user'].initial = current_filter.user_id

    edit_dict_condition = []

    model_klass_has_attr = hasattr(model_klass, 'extra_filter_fields')

    for condition in current_filter.conditions.filter(~Q(champ__contains='relations') & ~Q(champ__contains='properties') & ~Q(type__pk=DATE_RANGE_FILTER)):
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

    date_filters_conditions = []
    for condition in current_filter.conditions.filter(Q(type__pk=DATE_RANGE_FILTER)):
        dates = list(condition.values.values_list('value', flat=True))
        dates.sort()
        date_filters_conditions.append({'date_field': condition.champ, 'begin_date': dates[0], 'end_date':dates[1]})

    return render_to_response('creme_core/filters.html',
                              {'form': filterform,
                               'mode': 'edit',
                               'edit_dict': edit_dict,
                               'content_type_id': ct_id,
                               'relations_conditions': rel_conditions,
                               'properties_conditions': prop_conditions,
                               'date_filters_conditions': date_filters_conditions
                              },
                              context_instance=RequestContext(request))


@login_required
def get_filters_4_ct(request, content_type_id):
    """
        @Returns filters' json list
    """
    ct = get_ct_or_404(content_type_id)
    filters = Filter.objects.filter(model_ct=ct)
    fields = request.GET.getlist('fields') or ('name', )

    data = serializers.serialize('json', filters, fields=fields)
    return HttpResponse(data, mimetype="text/javascript")


@jsonify
@login_required
def field_has_n_get_fk(request):
    """
    To verify if a field is a foreign key for a model
    and if it is get related field (in JSON format)
    """

    fieldname = get_from_POST_or_404(request.POST, 'fieldname')
    ct_id     = get_from_POST_or_404(request.POST, 'ct_id')
    klass     = get_ct_or_404(ct_id).model_class()


    field = [f for f in klass._meta.fields + klass._meta.many_to_many if f.name == fieldname]
    data  = []

    if field and field[0].get_internal_type() == 'ForeignKey':
        data = [(u'%s' % f.name, u'%s' % f.verbose_name) for f in get_flds_with_fk_flds(field[0].rel.to, 0)]

    elif field and field[0].get_internal_type() == 'ManyToManyField':
        data = []

        for f in get_flds_with_fk_flds(field[0].rel.to, 0):
            _field_internal_type = f.get_internal_type()

            if _field_internal_type == 'ManyToManyField':
                continue

            if _field_internal_type != 'ForeignKey':
                data.append((u'%s' % f.name, u'%s' % f.verbose_name))

            if _field_internal_type == 'ForeignKey':
                data.extend(((u'%s__%s' % (f.name, sub_f.name), u'%s - %s' % (f.verbose_name, sub_f.verbose_name)) for sub_f in get_flds_with_fk_flds(f.rel.to, 0)))

    return data