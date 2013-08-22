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

from django.http import Http404, HttpResponse
from django.db.models import ForeignKey, ManyToManyField, Q
from django.shortcuts import get_object_or_404, render
from django.utils.timezone import now
from django.utils.translation import ugettext as _
#from django.utils.simplejson import JSONEncoder
from django.utils.encoding import smart_str
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.contenttypes.models import ContentType

from creme.creme_core.models import CremeEntity, RelationType
from creme.creme_core.utils.date_range import date_range_registry
from creme.creme_core.views.generic import (add_entity, edit_entity, view_entity,
                                            list_view, inner_popup, add_to_entity)
from creme.creme_core.utils.meta import get_model_field_info, get_related_field #ModelFieldEnumerator
from creme.creme_core.utils import get_ct_or_404, get_from_POST_or_404 #jsonify
from creme.creme_core.registry import export_backend_registry

from ..models import Report, Field
from ..models.report import HFI_FIELD, HFI_RELATION, HFI_RELATED #TODO: true report constant...
from ..forms.report import (CreateForm, EditForm, LinkFieldToReportForm,
                            AddFieldToReportForm, DateReportFilterForm) #get_aggregate_custom_fields
#from ..report_aggregation_registry import field_aggregation_registry
from ..utils import decode_datetime


@login_required
@permission_required('reports')
@permission_required('reports.add_report')
def add(request):
    return add_entity(request, CreateForm, template="reports/add_report.html", #TODO: improve widgets & drop this template
                      #extra_template_dict={'help_messages': [],
                                           #'ct_posted':     request.POST.get('ct'),
                                          #}
                     )

@login_required
@permission_required('reports')
def edit(request, report_id):
    return edit_entity(request, report_id, Report, EditForm)

@login_required
@permission_required('reports')
def detailview(request, report_id):
    return view_entity(request, report_id, Report, '/reports/report', 'reports/view_report.html')

@login_required
@permission_required('reports')
def listview(request):
    return list_view(request, Report, extra_dict={'add_url': '/reports/report/add'})

@login_required
@permission_required('reports')
def unlink_report(request):
    field = get_object_or_404(Field, pk=get_from_POST_or_404(request.POST, 'field_id'))

    try: #TODO: will be deleted when M2M has been replaced by a FK...
        current_report = field.report_columns_set.all()[0]
    except IndexError:
        pass #Should never get here...
    else:
        has_perm_or_die = request.user.has_perm_to_unlink_or_die
        has_perm_or_die(current_report)

        if field.report is None:
            raise Http404('This field has no sub-report') #TODO: ConflictError

        has_perm_or_die(field.report)

        field.report   = None
        field.selected = False
        field.save()

    return HttpResponse("", mimetype="text/javascript")

def _link_report(request, report, field, ct):
    request.user.has_perm_to_link_or_die(report)

    if request.method == 'POST':
        link_form = LinkFieldToReportForm(report, field, ct, user=request.user, data=request.POST)

        if link_form.is_valid():
            link_form.save()
    else:
        link_form = LinkFieldToReportForm(report=report, field=field, ct=ct, user=request.user)

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {'form':   link_form,
                        'title': _(u'Link of the column <%s>') % field,
                       },
                       is_valid=link_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )

@login_required
@permission_required('reports')
def link_report(request, report_id, field_id):
    field  = get_object_or_404(Field,  pk=field_id)

    if field.type != HFI_FIELD:
        raise Http404('This does not represent a model field') #TODO: ConflictError

    report = get_object_or_404(Report, pk=report_id)

    for info in get_model_field_info(report.ct.model_class(), field.name):
        if isinstance(info['field'], (ForeignKey, ManyToManyField)):
            model = info['model']
            break
    else:
        raise Http404('This field is not a ForeignKey/ManyToManyField') #TODO: ConflictError

    ct = ContentType.objects.get_for_model(model)

    if not issubclass(model, CremeEntity):
        raise Http404('The related model does not inherit CremeEntity') #TODO: ConflictError

    return _link_report(request, report, field, ct)

@login_required
@permission_required('reports')
def link_relation_report(request, report_id, field_id, ct_id):
    rfield  = get_object_or_404(Field, pk=field_id)

    if rfield.type != HFI_RELATION:
        raise Http404('This does not represent a Relationship') #TODO: ConflictError

    ct = get_ct_or_404(ct_id)

    if not RelationType.objects.get(symmetric_type=rfield.name).is_compatible(ct.id):
        raise Http404('This ContentType is not compatible with the RelationType') #TODO: ConflictError

    report = get_object_or_404(Report, pk=report_id)

    return _link_report(request, report, rfield, ct)

@login_required
@permission_required('reports')
def link_related_report(request, report_id, field_id):
    rfield  = get_object_or_404(Field,  pk=field_id)

    if rfield.type != HFI_RELATED:
        raise Http404('This does not represent a related model') #TODO: ConflictError

    report = get_object_or_404(Report, pk=report_id)

    if report.id not in rfield.report_columns_set.values_list('pk', flat=True):
        return HttpResponse("", status=403, mimetype="text/javascript")

    related_field = get_related_field(report.ct.model_class(), rfield.name)

    if related_field is None:
        #should not happen (if form is not buggy of course)
        raise Http404('This field is invalid') #TODO: ConflictError

    ct = ContentType.objects.get_for_model(related_field.model)

    return _link_report(request, report, rfield, ct)

@login_required
@permission_required('reports')
def add_field(request, report_id):
    return add_to_entity(request, report_id, AddFieldToReportForm,
                         _(u'Adding column to <%s>'),
                        )

_order_direction = {
    'up':   -1,
    'down':  1,
}

@login_required
@permission_required('reports')
def change_field_order(request):
    POST = request.POST
    report = get_object_or_404(Report, pk=get_from_POST_or_404(POST,'report_id'))
    field  = get_object_or_404(Field,  pk=get_from_POST_or_404(POST,'field_id'))
    direction = POST.get('direction', 'up')

    if report.id not in field.report_columns_set.values_list('pk', flat=True):
        return HttpResponse("", status=403, mimetype="text/javascript")

    request.user.has_perm_to_change_or_die(report)

    field.order =  field.order + _order_direction[direction]
    try:
        other_field = report.columns.get(order=field.order)
    except Field.DoesNotExist:
        return HttpResponse("", status=403, mimetype="text/javascript")

    other_field.order = other_field.order - _order_direction[direction]

    field.save()
    other_field.save()

    return HttpResponse("", status=200, mimetype="text/javascript")

@login_required
@permission_required('reports')
def preview(request, report_id):
    user = request.user
    report = get_object_or_404(Report, pk=report_id)

    user.has_perm_to_view_or_die(report)

    extra_q_filter = Q()
    start = end = None

    if request.method == 'POST':
        filter_form = DateReportFilterForm(report=report, user=user, data=request.POST)

        if filter_form.is_valid():
            q_dict = filter_form.get_q_dict()
            start, end = filter_form.get_dates()
            if q_dict is not None:
                extra_q_filter = Q(**filter_form.get_q_dict())
    else:
        filter_form = DateReportFilterForm(report=report, user=user)

    LIMIT_TO = 25

    return render(request, "reports/preview_report.html",
                  {'lines': report.fetch_all_lines(limit_to=LIMIT_TO,
                                                   extra_q=extra_q_filter,
                                                   user=user,
                                                  ),
                   'object':   report,
                   'limit_to': LIMIT_TO,
                   'form':     filter_form,
                   'start':    start,
                   'end':      end,
                   },
                 )

@login_required
@permission_required('reports')
def set_selected(request):
    POST   = request.POST
    rfield  = get_object_or_404(Field,  pk=get_from_POST_or_404(POST, 'field_id'))

    if not rfield.report_id:
        raise Http404('This Field has no Report, so can no be (un)selected') #TODO: ConflictError

    report = get_object_or_404(Report, pk=get_from_POST_or_404(POST, 'report_id'))

    if report.id not in rfield.report_columns_set.values_list('pk', flat=True):
        return HttpResponse("Forbidden", status=403, mimetype="text/javascript")

    request.user.has_perm_to_change_or_die(report)

    try:
        checked = bool(int(POST.get('checked', 0)))
    except ValueError:
        checked = False

    if rfield.selected != checked:
        if checked: #Only one Field should be selected
            report.columns.exclude(pk=rfield.pk).update(selected=False)

        rfield.selected = checked
        rfield.save()

    return HttpResponse(mimetype="text/javascript")

@login_required
@permission_required('reports')
def export(request, report_id, doc_type):
    report         = get_object_or_404(Report, pk=report_id)
    GET_get        = request.GET.get
    user           = request.user
    extra_q_filter = None

    backend = export_backend_registry.get_backend(doc_type)
    if backend is None:
        raise Http404('Unknown extension')

    writer = backend()
    writerow = writer.writerow

    user.has_perm_to_view_or_die(report)

    field_name = GET_get('field')
    if field_name is not None:
        dt_range_name = GET_get('range_name')  # Empty str should get CustomRange

        dt_range = date_range_registry.get_range(dt_range_name,
                                                 decode_datetime(GET_get('start')),
                                                 decode_datetime(GET_get('end')))

        if dt_range is not None:
            extra_q_filter = Q(**dt_range.get_q_dict(field_name, now()))

    writerow([smart_str(column.title) for column in report.get_children_fields_flat()])

    for line in report.fetch_all_lines(extra_q=extra_q_filter, user=user):
        writerow([smart_str(value) for value in line])

    writer.save(smart_str(report.name))

    return writer.response

##todo: factorise with forms.report.AddFieldToReportForm._set_aggregate_fields
#@login_required
##@permission_required('reports') ??
#@jsonify
#def get_aggregate_fields(request):
    #POST = request.POST
    #aggregate_name = POST.get('aggregate_name')
    #ct = get_ct_or_404(get_from_POST_or_404(POST, 'ct_id'))
    #choices = []

    #if aggregate_name:
        #aggregate = field_aggregation_registry.get(aggregate_name)

        #if aggregate:
            #model = ct.model_class()
            #aggregate_pattern = aggregate.pattern
            #authorized_fields = field_aggregation_registry.authorized_fields
            #choices = [(aggregate_pattern % f_name, f_vname)
                            #for f_name, f_vname in ModelFieldEnumerator(model, deep=0)
                                                    #.filter((lambda f: isinstance(f, authorized_fields)), viewable=True)
                                                    #.choices()
                      #]

            #choices.extend(get_aggregate_custom_fields(model, aggregate_pattern))

    ##return HttpResponse(JSONEncoder().encode(choices), mimetype="text/javascript")
    #return choices

@login_required
@permission_required('reports')
def date_filter_form(request, report_id):
    report = get_object_or_404(Report, pk=report_id)
    request.user.has_perm_to_view_or_die(report)

    callback_url = None

    if request.method == 'POST':
        form = DateReportFilterForm(report=report, user=request.user, data=request.POST)
        if form.is_valid():
            callback_url = '/reports/report/export/%s/%s%s' % (
                                    report_id,
                                    form.cleaned_data.get('doc_type'),
                                    form.forge_url_data,
                                )
    else:
        form = DateReportFilterForm(report=report, user=request.user)

    return inner_popup(request, 'reports/frags/date_filter_form.html',
                       {'form':            form,
                        'title':           _(u'Temporal filters for <%s>' % report),
                        'inner_popup':     True,
                        'report_id':       report_id,
                       },
                       is_valid=form.is_valid(),
                       reload=True,
                       delegate_reload=False,
                       callback_url=callback_url,
                      )

#@jsonify
#@login_required
#def get_predicates_choices_4_ct(request): #todo: move to creme_core ???
    #ct = get_ct_or_404(get_from_POST_or_404(request.POST, 'ct_id'))  #todo: why not GET ??
    #return [(rtype.id, rtype.predicate)
                #for rtype in RelationType.get_compatible_ones(ct, include_internals=True)
                                         #.order_by('predicate') #todo: move in RelationType meta ??
           #]

#@jsonify
#@login_required
#@permission_required('reports')
#def get_related_fields(request):
    #ct = get_ct_or_404(get_from_POST_or_404(request.POST, 'ct_id')) #todo: why not GET ??
    #return Report.get_related_fields_choices(ct.model_class())
