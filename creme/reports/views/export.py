# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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
from typing import Type

from django.forms.forms import BaseForm
from django.urls import reverse
from django.utils.encoding import smart_str
from django.utils.translation import gettext as _
from django.utils.translation import pgettext_lazy

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.views import generic

from .. import get_report_model
from ..forms import report as report_forms

logger = logging.getLogger(__name__)
Report = get_report_model()


class Preview(generic.EntityDetail):
    model = Report
    template_name = 'reports/preview_report.html'
    pk_url_kwarg = 'report_id'
    filter_form_class = report_forms.ReportExportPreviewFilterForm
    limit_count = 25

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        report = self.object
        user = request.user
        form = self.filter_form_class(report=report, user=user, data=request.GET)
        lines = self.get_lines(form)

        context['lines'] = lines
        context['form'] = form
        context['limit_to'] = self.limit_count
        context['flat_columns'] = [*report.get_children_fields_flat()]
        context['empty_message'] = self.get_empty_message(form, lines)

        return context

    def get_empty_message(self, form, lines):
        if form.is_valid():
            if lines:
                empty_message = ''
            else:
                report = self.object
                user = self.request.user
                ct = report.ct

                if not EntityCredentials.filter(user, ct.model_class().objects.all()).exists():
                    empty_message = _('You can see no «{model}»').format(model=ct)
                elif report.filter and not report.fetch_all_lines(limit_to=1, user=user):
                    empty_message = _('No «{model}» matches the filter «{filter}»').format(
                        model=ct,
                        filter=report.filter,
                    )
                else:
                    empty_message = _('No «{model}» matches your date filter').format(model=ct)
        else:
            empty_message = _('Fix your date filter')

        return empty_message

    def get_lines(self, form):
        return self.object.fetch_all_lines(
            limit_to=self.limit_count,
            extra_q=form.get_q(),
            user=self.request.user,
        ) if form.is_valid() else []


class ExportFilterURL(generic.EntityEditionPopup):
    model = Report
    form_class: Type[BaseForm] = report_forms.ReportExportFilterForm
    template_name = 'reports/forms/report-export-filter.html'
    pk_url_kwarg = 'report_id'
    title = pgettext_lazy('reports-report', 'Export «{object}»')
    submit_label = pgettext_lazy('reports-report', 'Export')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.export_url = ''

    def check_instance_permissions(self, instance, user):
        user.has_perm_to_view_or_die(instance)

    def form_valid(self, form):
        self.export_url = '{}?{}'.format(
            reverse('reports__export_report', args=(self.object.id,)),
            form.export_url_data(),
        )
        return super().form_valid(form=form)

    def get_success_url(self):
        return self.export_url


class Export(generic.base.EntityRelatedMixin, generic.CheckedView):
    permissions = 'reports'
    entity_id_url_kwarg = 'report_id'
    entity_classes = Report
    form_class = report_forms.ReportExportFilterForm

    def check_related_entity_permissions(self, entity, user):
        user.has_perm_to_view_or_die(entity)

    def get_form(self, *, report, request):
        form = self.form_class(instance=report, user=request.user, data=request.GET)

        if not form.is_valid():
            logger.warning('Error in reports.export(): %s', form.errors)
            raise ConflictError('Invalid export filter')

        return form

    def get(self, request, *args, **kwargs):
        user = request.user
        report = self.get_related_entity()
        form = self.get_form(report=report, request=request)

        q_filter = form.get_q()
        writer = form.get_backend()

        if writer is None:
            raise ConflictError('Unknown extension')

        writerow = writer.writerow

        writerow([
            smart_str(column.title) for column in report.get_children_fields_flat()
        ])

        for line in report.fetch_all_lines(extra_q=q_filter, user=user):
            writerow([smart_str(value) for value in line])

        writer.save(smart_str(report.name), user)

        return writer.response
