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

from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext_lazy as _, gettext

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import (
    CustomField, CustomFieldEnumValue,
    Job, DeletionCommand,
)
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic
from creme.creme_core.views.bricks import BricksReloading
from creme.creme_core.views.generic.base import EntityCTypeRelatedMixin

from ..bricks import CustomEnumsBrick
from ..forms import custom_fields as cf_forms

from . import base


class FirstCTypeCustomFieldCreation(base.ConfigModelCreation):
    model = CustomField
    form_class = cf_forms.CustomFieldsCTAddForm
    title = _('New custom field configuration')


class CustomFieldCreation(EntityCTypeRelatedMixin,
                          base.ConfigModelCreation,
                         ):
    model = CustomField
    form_class = cf_forms.CustomFieldsAddForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['ctype'] = self.get_ctype()

        return kwargs

    def get_title(self):
        return gettext('New custom field for «{model}»').format(
            model=self.get_ctype(),
        )


class Portal(generic.BricksView):
    # template_name = 'creme_config/custom_fields_portal.html'
    template_name = 'creme_config/custom_field/portal.html'


class CustomFieldEdition(base.ConfigModelEdition):
    model = CustomField
    # form_class = cf_forms.CustomFieldsEditForm
    form_class = cf_forms.CustomFieldEditionForm
    pk_url_kwarg = 'field_id'


class CTypeCustomFieldsDeletion(base.ConfigDeletion):
    ct_id_arg = 'id'

    def perform_deletion(self, request):
        for field in CustomField.objects.filter(
            content_type=get_from_POST_or_404(request.POST, self.ct_id_arg),
        ):
            field.delete()


class CustomFieldDeletion(base.ConfigDeletion):
    id_arg = 'id'

    def perform_deletion(self, request):
        get_object_or_404(
            CustomField,
            id=get_from_POST_or_404(request.POST, self.id_arg),
        ).delete()


class EnumMixin:
    def check_custom_field(self, cfield):
        if cfield.field_type not in (CustomField.ENUM, CustomField.MULTI_ENUM):
            raise ConflictError('Only ENUM/MULTI_ENUM are allowed.')


class CustomEnumsDetail(EnumMixin, generic.CremeModelDetail):
    model = CustomField
    template_name = 'creme_config/custom_field/enums.html'
    pk_url_kwarg = 'field_id'
    context_object_name = 'custom_field'
    bricks_reload_url_name = 'creme_config__reload_custom_enum_brick'

    def check_instance_permissions(self, instance, user):
        self.check_custom_field(instance)


class CustomEnumsAdding(EnumMixin, base.ConfigModelEdition):
    model = CustomField
    form_class = cf_forms.CustomEnumsAddingForm
    pk_url_kwarg = 'field_id'
    submit_label = _('Add these new choices')

    def check_instance_permissions(self, instance, user):
        self.check_custom_field(instance)


class CustomEnumEdition(base.ConfigModelEdition):
    model = CustomFieldEnumValue
    pk_url_kwarg = 'enum_id'
    form_class = cf_forms.CustomEnumEditionForm


class CustomEnumDeletion(base.ConfigModelEdition):
    model = CustomFieldEnumValue
    pk_url_kwarg = 'enum_id'
    form_class = cf_forms.CustomEnumDeletionForm
    template_name = 'creme_core/generics/blockform/delete-popup.html'
    job_template_name = 'creme_config/deletion-job-popup.html'
    title = _('Replace & delete «{object}»')
    submit_label = _('Delete the choice')

    # TODO: factorise with .generics_views.GenericDeletion
    def check_instance_permissions(self, instance, user):
        dcom = DeletionCommand.objects.filter(
            content_type=ContentType.objects.get_for_model(type(instance)),
        ).first()

        if dcom is not None:
            if dcom.job.status == Job.STATUS_OK:
                dcom.job.delete()
            else:
                # TODO: if STATUS_ERROR, show a popup with the errors ?
                raise ConflictError(
                    gettext('A deletion process for a choice already exists.')
                )

    def form_valid(self, form):
        self.object = form.save()

        return render(
            request=self.request,
            template_name=self.job_template_name,
            context={'job': self.object.job},
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = None
        kwargs['choice_to_delete'] = self.object

        return kwargs


class CustomEnumBrickReloading(BricksReloading):
    permissions = base._PERM
    check_bricks_permission = False
    pk_url_kwarg = 'field_id'

    def get_bricks_context(self):
        context = super().get_bricks_context()
        # Not useful to check if it's an enum field, because not a security issue.
        context['custom_field'] = get_object_or_404(
            CustomField,
            pk=self.kwargs[self.pk_url_kwarg],
        )

        return context

    def get_brick_ids(self):
        return [CustomEnumsBrick.id_]
