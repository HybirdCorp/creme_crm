# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

import logging

from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils.encoding import smart_str
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views.generic import inner_popup

from ..forms.report import ReportExportPreviewFilterForm, ReportExportFilterForm
from ..models import Report


logger = logging.getLogger(__name__)

_PREVIEW_LIMIT_COUNT = 25

@login_required
@permission_required('reports')
def preview(request, report_id):
    user = request.user
    report = get_object_or_404(Report, pk=report_id)

    user.has_perm_to_view_or_die(report)

    filter = ReportExportPreviewFilterForm(report=report, user=user, data=request.GET)
    lines = []

    if filter.is_valid():
        lines = report.fetch_all_lines(limit_to=_PREVIEW_LIMIT_COUNT,
                                       extra_q=filter.get_q(),
                                       user=user,
                                      )

    return render(request, "reports/preview_report.html",
                  {'lines':    lines,
                   'object':   report,
                   'limit_to': _PREVIEW_LIMIT_COUNT,
                   'form':     filter,
                  },
                 )

@login_required
@permission_required('reports')
def filter(request, report_id):
    user = request.user
    report = get_object_or_404(Report, pk=report_id)
    callback_url = ''

    user.has_perm_to_view_or_die(report)

    if request.method == 'POST':
        form = ReportExportFilterForm(report=report, user=user, data=request.POST)
        if form.is_valid():
            callback_url = '/reports/export/%s?%s' % (report_id, form.export_url_data())
    else:
        form = ReportExportFilterForm(report=report, user=user)

    return inner_popup(request, 'reports/frags/report_export_filter.html',
                       {'form':            form,
                        'title':           _(u'Export <%s>' % report),
                        'inner_popup':     True,
                        'report_id':       report_id,
                       },
                       is_valid=form.is_valid(),
                       reload=True,
                       delegate_reload=False,
                       callback_url=mark_safe(callback_url),
                      )


@login_required
@permission_required('reports')
def export(request, report_id):
    user = request.user
    report = get_object_or_404(Report, pk=report_id)

    user.has_perm_to_view_or_die(report)

    form = ReportExportFilterForm(report=report, user=user, data=request.GET)

    if not form.is_valid():
        logger.warn('Error in reports.export(): %s', form.errors)
        raise Http404('Invalid export filter')

    q_filter = form.get_q()
    backend = form.get_backend()

    if backend is None:
        raise Http404('Unknown extension')

    writer = backend()
    writerow = writer.writerow

    writerow([smart_str(column.title) for column in report.get_children_fields_flat()])

    for line in report.fetch_all_lines(extra_q=q_filter, user=user):
        writerow([smart_str(value) for value in line])

    writer.save(smart_str(report.name))
    return writer.response
