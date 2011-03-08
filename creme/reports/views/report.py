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

from datetime import datetime
from logging import debug

from django.http import Http404, HttpResponse
from django.db.models import ForeignKey, ManyToManyField, FieldDoesNotExist, Q
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.utils.simplejson import JSONEncoder
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.contenttypes.models import ContentType

from creme_core.views.generic import (add_entity, edit_entity, view_entity,
                                      list_view, inner_popup, add_to_entity)
from creme_core.utils.meta import get_model_field_infos, get_flds_with_fk_flds, get_date_fields, is_date_field
from creme_core.utils import get_ct_or_404, get_from_GET_or_404, get_from_POST_or_404
from creme_core.date_filters_registry import date_filters_registry

from reports.models import Report, Field
from reports.forms.report import CreateForm, EditForm, LinkFieldToReportForm, AddFieldToReportForm, get_aggregate_custom_fields, DateReportFilterForm
from reports.registry import report_backend_registry
from reports.report_aggregation_registry import field_aggregation_registry


@login_required
@permission_required('reports')
@permission_required('reports.add_report')
def add(request):
    return add_entity(request, CreateForm, template="reports/add_report.html",
                      extra_template_dict={
                                            'help_messages': [],
                                            'ct_posted':     request.POST.get('ct'),
                                          }
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
    field = get_object_or_404(Field, pk=request.POST.get('field_id'))
    user  = request.user

    current_report = None
    try:
        current_report = field.report_columns_set.all()[0]
        current_report.can_unlink_or_die(user)#User can unlink on current report
    except IndexError:
        pass#Should never get here...

    if current_report is not None:
        field.report.can_unlink_or_die(user)#User can unlink on sub report

        field.report   = None
        field.selected = False
        field.save()

    return HttpResponse("", mimetype="text/javascript")

def __link_report(request, report, field, ct):
    report.can_link_or_die(request.user)

    #POST = request.POST
    #if POST:
    if request.method == 'POST':
        #link_form = LinkFieldToReportForm(report, field, ct, POST)
        link_form = LinkFieldToReportForm(report, field, ct, user=request.user, data=request.POST)

        if link_form.is_valid():
            link_form.save()
    else:
        #link_form = LinkFieldToReportForm(report=report, field=field, ct=ct)
        link_form = LinkFieldToReportForm(report=report, field=field, ct=ct, user=request.user)

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {
                        'form':   link_form,
                        'title': _(u'Link of the column <%s>') % field,
                       },
                       is_valid=link_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request)
                      )

@login_required
@permission_required('reports')
def link_report(request, report_id, field_id):
    field  = get_object_or_404(Field,  pk=field_id)
    report = get_object_or_404(Report, pk=report_id)

    fields = get_model_field_infos(report.ct.model_class(), field.name)

    model = None
    for f in fields:
        if isinstance(f.get('field'), (ForeignKey, ManyToManyField)):
            model = f.get('model') #TODO: break ??

    if model is None:
        raise Http404

    ct = ContentType.objects.get_for_model(model)

    return __link_report(request, report, field, ct)

@login_required
@permission_required('reports')
def link_relation_report(request, report_id, field_id, ct_id):
    field  = get_object_or_404(Field,  pk=field_id)
    report = get_object_or_404(Report, pk=report_id)
    ct = get_ct_or_404(ct_id)

    return __link_report(request, report, field, ct)


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

    report.can_change_or_die(request.user)

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
    report = get_object_or_404(Report, pk=report_id)
    report.can_view_or_die(request.user)

    extra_q_filter = Q()

    if request.method == 'POST':
        filter_form = DateReportFilterForm(report=report, user=request.user, data=request.POST)

        if filter_form.is_valid():
            extra_q_filter = filter_form.get_q()
    else:
        filter_form = DateReportFilterForm(report=report, user=request.user)

    LIMIT_TO = 25
    html_backend = report_backend_registry.get_backend('HTML')
    req_ctx = RequestContext(request)
    html_backend = html_backend(report, context_instance=req_ctx, limit_to=LIMIT_TO, extra_fetch_q=extra_q_filter) #reusing the same variable is not great

    return render_to_response("reports/preview_report.html",
                              {
                                'object':        report,
                                'html_backend':  html_backend,
                                'limit_to':      LIMIT_TO,
                                'date_filters':  date_filters_registry.itervalues(),
                                'date_fields':   [(field.name, field.verbose_name) for field in get_date_fields(report.ct.model_class())],
                                'form':          filter_form,
                              },
                              context_instance=req_ctx)

@login_required
@permission_required('reports')
def set_selected(request):
    POST   = request.POST
    report = get_object_or_404(Report, pk=POST.get('report_id')) #TODO: use get_from_POST_or_404()
    field  = get_object_or_404(Field,  pk=POST.get('field_id'))

    report.can_change_or_die(request.user)

    try:
        checked = int(POST.get('checked', 0))
    except ValueError:
        checked = 0
    checked = bool(checked)

    #Ensure all other fields are un-selected
    for column in report.columns.all():
        column.selected = False
        column.save()

    if checked:
        field.selected = True
        field.save()

    return HttpResponse("", status=200, mimetype="text/javascript")

@login_required
@permission_required('reports')
def csv(request, report_id):
    report = get_object_or_404(Report, pk=report_id)
    csv_backend = report_backend_registry.get_backend('CSV')
    GET  = request.GET
    user = request.user

    report.can_view_or_die(user)

    if GET: #TODO: request.method == 'GET' => Post TODO: Doesn't work
        field_name = get_from_GET_or_404(GET, 'field')
        try:
            if not is_date_field(report.ct.model_class()._meta.get_field(field_name)):
                raise Http404('%s is not a date field' % field_name)
        except FieldDoesNotExist, e:
            raise Http404(str(e))

        from_ts = lambda s: datetime.fromtimestamp(float(get_from_GET_or_404(GET, s)))
        try:
            start_date = from_ts('start')
            end_date   = from_ts('end')
        except (ValueError, TypeError), e:
            raise Http404('Bad date input (%s)' % e)

        extra_q_filter = Q(**{str("%s__range" % field_name): (start_date, end_date)})
    else:
        extra_q_filter = Q()

    return csv_backend(report, extra_q_filter, user).render_to_response()

@login_required
#@permission_required('reports') ??
def get_aggregate_fields(request):
    POST_get = request.POST.get
    aggregate_name = POST_get('aggregate_name')
    ct = get_ct_or_404(get_from_POST_or_404(request.POST, 'ct_id'))
    model = ct.model_class()
    authorized_fields = field_aggregation_registry.authorized_fields
    choices = []

    if aggregate_name:
        aggregate = field_aggregation_registry.get(aggregate_name)
        aggregate_pattern = aggregate.pattern
        choices = [(u"%s" % (aggregate_pattern % f.name), unicode(f.verbose_name)) for f in get_flds_with_fk_flds(model, deep=0) if f.__class__ in authorized_fields]
        choices.extend(get_aggregate_custom_fields(model, aggregate_pattern))

    return HttpResponse(JSONEncoder().encode(choices), mimetype="text/javascript")

@login_required
#@permission_required('reports') ??
def date_filter_form(request, report_id):
    report = get_object_or_404(Report, pk=report_id)

    redirect = False
    simple_redirect = False
    valid = False

    if request.method == 'POST':
        form = DateReportFilterForm(report=report, user=request.user, data=request.POST)
        redirect = True
        valid = True
        if not form.is_valid():
           simple_redirect = True
    else:
        form = DateReportFilterForm(report=report, user=request.user)

    return inner_popup(request, 'reports/frags/date_filter_form.html',
                       {
                        'form':            form,
                        'title':           _(u'Temporal filters for <%s>' % report),
                        'inner_popup':     True,
                        'report_id':       report_id,
                        'redirect':        redirect,
                        'simple_redirect': simple_redirect,
                       },
                       is_valid=valid,
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))
