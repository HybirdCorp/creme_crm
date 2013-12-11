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
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.utils.timezone import now
from django.utils.translation import ugettext as _
from django.utils.encoding import smart_str
from django.contrib.auth.decorators import login_required, permission_required

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.utils import get_from_POST_or_404 #jsonify
from creme.creme_core.utils.date_range import date_range_registry
from creme.creme_core.views.generic import (add_entity, edit_entity, view_entity,
                                            list_view, inner_popup, add_to_entity)
from creme.creme_core.registry import export_backend_registry

from ..forms.report import (ReportCreateForm, ReportEditForm, LinkFieldToReportForm,
                            ReportFieldsForm, DateReportFilterForm)
from ..models import Report, Field
from ..utils import decode_datetime


@login_required
@permission_required('reports')
@permission_required('reports.add_report')
def add(request):
    return add_entity(request, ReportCreateForm, template="reports/add_report.html", #TODO: improve widgets & drop this template
                      extra_template_dict={'submit_label': _('Save the report'),
                                           #'help_messages': [],
                                           #'ct_posted':     request.POST.get('ct'),
                                          }
                     )

@login_required
@permission_required('reports')
def edit(request, report_id):
    return edit_entity(request, report_id, Report, ReportEditForm)

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

    #TODO: odd credentials ?! (only edit on field.report ??)
    has_perm_or_die = request.user.has_perm_to_unlink_or_die
    has_perm_or_die(field.report)

    if field.sub_report is None:
        raise ConflictError('This field has no sub-report')

    has_perm_or_die(field.sub_report)

    field.sub_report = None
    field.selected = False
    field.save()

    return HttpResponse("", mimetype="text/javascript")

@login_required
@permission_required('reports')
def link_report(request, field_id):
    rfield = get_object_or_404(Field, pk=field_id)
    user = request.user

    user.has_perm_to_link_or_die(rfield.report)

    hand = rfield.hand

    if hand is None:
        raise ConflictError('This field is invalid') #TODO: force block to reload

    ctypes = rfield.hand.get_linkable_ctypes()

    if ctypes is None:
        raise ConflictError('This field is not linkable')

    if request.method == 'POST':
        link_form = LinkFieldToReportForm(rfield, ctypes, user=user, data=request.POST)

        if link_form.is_valid():
            link_form.save()
    else:
        link_form = LinkFieldToReportForm(rfield, ctypes, user=user)

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {'form':   link_form,
                        'title': _(u'Link of the column <%s>') % rfield,
                       },
                       is_valid=link_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )

@login_required
@permission_required('reports')
def edit_fields(request, report_id):
    return add_to_entity(request, report_id, ReportFieldsForm,
                         _(u'Edit columns of <%s>'),
                        )

_order_direction = {
    'up':   -1,
    'down':  1,
}

@login_required
@permission_required('reports')
def change_field_order(request):
    POST = request.POST
    field = get_object_or_404(Field, pk=get_from_POST_or_404(POST, 'field_id'))
    direction = POST.get('direction', 'up')
    report = field.report

    request.user.has_perm_to_change_or_die(report)

    field.order = field.order + _order_direction[direction] #TODO: manage bad direction arg
    try:
        other_field = report.fields.get(order=field.order)
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

#TODO: jsonify ?
@login_required
@permission_required('reports')
def set_selected(request):
    POST   = request.POST
    rfield = get_object_or_404(Field, pk=get_from_POST_or_404(POST, 'field_id'))

    if not rfield.sub_report_id:
        raise ConflictError('This Field has no Report, so can no be (un)selected')

    report = rfield.report

    request.user.has_perm_to_change_or_die(report)

    try:
        checked = bool(int(POST.get('checked', 0)))
    except ValueError:
        checked = False

    if rfield.selected != checked:
        if checked: #Only one Field should be selected
            report.fields.exclude(pk=rfield.pk).update(selected=False)

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
                                                 decode_datetime(GET_get('end')),
                                                )

        if dt_range is not None:
            extra_q_filter = Q(**dt_range.get_q_dict(field_name, now()))

    writerow([smart_str(column.title) for column in report.get_children_fields_flat()])

    for line in report.fetch_all_lines(extra_q=extra_q_filter, user=user):
        writerow([smart_str(value) for value in line])

    writer.save(smart_str(report.name))

    return writer.response

@login_required
@permission_required('reports')
def date_filter_form(request, report_id):
    report = get_object_or_404(Report, pk=report_id)
    user = request.user

    user.has_perm_to_view_or_die(report)

    callback_url = None

    if request.method == 'POST':
        form = DateReportFilterForm(report=report, user=user, data=request.POST)
        if form.is_valid():
            callback_url = '/reports/report/export/%s/%s%s' % (
                                    report_id,
                                    form.cleaned_data.get('doc_type'),
                                    form.forge_url_data,
                                )
    else:
        form = DateReportFilterForm(report=report, user=user)

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
