# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

from django.db.transaction import atomic
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

# from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic
from creme.creme_core.views.generic.order import ReorderInstances

from .. import get_report_model
from ..constants import DEFAULT_HFILTER_REPORT
from ..forms import report as report_forms
from ..models import Field

logger = logging.getLogger(__name__)
Report = get_report_model()


# @login_required
# @permission_required('reports')
# def unlink_report(request):
#     field_id = get_from_POST_or_404(request.POST, 'field_id')
#
#     with atomic():
#         try:
#             rfield = Field.objects.select_for_update().get(pk=field_id)
#         except Field.DoesNotExist as e:
#             raise Http404(str(e)) from e
#
#         has_perm_or_die = request.user.has_perm_to_unlink_or_die
#         has_perm_or_die(rfield.report)
#
#         if rfield.sub_report is None:
#             raise ConflictError('This field has no sub-report')
#
#         has_perm_or_die(rfield.sub_report)
#
#         rfield.sub_report = None
#         rfield.selected = False
#         rfield.save()
#
#     return HttpResponse()
class ReportUnlinking(generic.CheckedView):
    permissions = 'reports'
    model = Field
    rfield_id_arg = 'field_id'

    def check_rfield_permissions(self, rfield, user):
        # TODO: odd credentials ?! (only edit on field.report ??)
        has_perm_or_die = user.has_perm_to_unlink_or_die
        has_perm_or_die(rfield.report)

        if rfield.sub_report is None:
            raise ConflictError('This field has no sub-report')

        has_perm_or_die(rfield.sub_report)

    def get_rfield_id(self, request):
        return get_from_POST_or_404(request.POST, self.rfield_id_arg, cast=int)

    def get_rfield(self, rfield_id):
        model = self.model

        try:
            rfield = model.objects.select_for_update().get(pk=rfield_id)
        except model.DoesNotExist as e:
            raise Http404(str(e)) from e

        self.check_rfield_permissions(rfield, self.request.user)

        return rfield

    def post(self, request, *args, **kwargs):
        rfield_id = self.get_rfield_id(request)

        with atomic():
            rfield = self.get_rfield(rfield_id)
            rfield.sub_report = None
            rfield.selected = False
            rfield.save()

        return HttpResponse()


# NB: cannot use RelatedToEntityEdition because Field has no get_related_entity() method
class ReportLinking(generic.CremeModelEditionPopup):
    model = Field
    pk_url_kwarg = 'field_id'
    form_class = report_forms.LinkFieldToReportForm
    template_name = 'creme_core/generics/blockform/link-popup.html'
    permissions = 'reports'
    title = _('Link of the column «{object}»')
    submit_label = _('Link')

    def check_instance_permissions(self, instance, user):
        user.has_perm_to_link_or_die(instance.report)

    def get_linkable_ctypes(self):
        rfield = self.object

        hand = rfield.hand
        if hand is None:
            raise ConflictError('This field is invalid')  # TODO: force brick to reload

        ctypes = rfield.hand.get_linkable_ctypes()
        if ctypes is None:
            raise ConflictError('This field is not linkable')

        return ctypes

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['ctypes'] = self.get_linkable_ctypes()

        return kwargs


class FieldsEdition(generic.EntityEditionPopup):
    model = Report
    form_class = report_forms.ReportFieldsForm
    pk_url_kwarg = 'report_id'
    title = _('Edit columns of «{object}»')


class MoveField(ReorderInstances):
    pk_url_kwarg = 'field_id'
    report_id_url_kwarg = 'report_id'
    use_select_for_update = False  # We use our own select_for_update()

    def get_queryset(self):
        report = get_object_or_404(Report.objects.select_for_update(),
                                   id=self.kwargs[self.report_id_url_kwarg],
                                  )
        self.request.user.has_perm_to_change_or_die(report)

        return report.fields


# @login_required
# @permission_required('reports')
# def set_selected(request):
#     POST = request.POST
#     field_id  = get_from_POST_or_404(POST, 'field_id',  cast=int)
#     report_id = get_from_POST_or_404(POST, 'report_id', cast=int)
#
#     try:
#         checked = bool(int(POST.get('checked', 0)))
#     except ValueError:
#         checked = False
#
#     with atomic():
#         report = get_object_or_404(Report.objects.select_for_update(), id=report_id)
#         request.user.has_perm_to_change_or_die(report)
#
#         rfield = get_object_or_404(Field, id=field_id)
#
#         if rfield.report_id != report.id:
#             raise ConflictError('This Field & this Report do not match.')
#
#         if not rfield.sub_report_id:
#             raise ConflictError('This Field has no Report, so can no be (un)selected')
#
#         report = rfield.report
#
#         if rfield.selected != checked:
#             if checked:  # Only one Field should be selected
#                 report.fields.exclude(pk=rfield.pk).update(selected=False)
#
#             rfield.selected = checked
#             rfield.save()
#
#     return HttpResponse()
class FieldSelection(generic.base.EntityRelatedMixin, generic.CheckedView):
    permissions = 'reports'
    entity_classes = Report
    entity_select_for_update = True
    report_id_arg = 'report_id'
    rfield_id_arg = 'field_id'
    checked_arg = 'checked'

    def check_rfield(self, rfield, report):
        if rfield.report_id != report.id:  # NB: compare IDs to avoid a query
            raise ConflictError('This Field & this Report do not match.')

        if not rfield.sub_report_id:
            raise ConflictError('This Field has no Report, so can no be (un)selected')

    def get_checked(self):
        try:
            checked = bool(int(self.request.POST.get(self.checked_arg, 0)))
        except ValueError:
            checked = False

        return checked

    def get_rfield_id(self):
        return get_from_POST_or_404(self.request.POST, self.rfield_id_arg, cast=int)

    def get_rfield(self, report):
        rfield = get_object_or_404(Field, id=self.get_rfield_id())
        self.check_rfield(rfield, report)

        return rfield

    def get_related_entity_id(self):
        return get_from_POST_or_404(self.request.POST, self.report_id_arg, cast=int)

    def post(self, *args, **kwargs):
        checked = self.get_checked()

        with atomic():
            report = self.get_related_entity()
            rfield = self.get_rfield(report)

            if rfield.selected != checked:
                if checked:  # Only one Field should be selected
                    report.fields.exclude(pk=rfield.pk).update(selected=False)

                rfield.selected = checked
                rfield.save()

        return HttpResponse()


class ReportCreation(generic.EntityCreation):
    model = Report
    form_class = report_forms.ReportCreateForm
    template_name = 'reports/add_report.html'  # TODO: improve widgets & drop this template


class ReportDetail(generic.EntityDetail):
    model = Report
    template_name = 'reports/view_report.html'
    pk_url_kwarg = 'report_id'


class ReportEdition(generic.EntityEdition):
    model = Report
    form_class = report_forms.ReportEditForm
    pk_url_kwarg = 'report_id'


class ReportsList(generic.EntitiesList):
    model = Report
    default_headerfilter_id = DEFAULT_HFILTER_REPORT
