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

# import logging
from django.contrib.contenttypes.models import ContentType
# from django.db import IntegrityError
# from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from creme.creme_core import utils
from creme.creme_core.core.exceptions import ConflictError
# from creme.creme_core.models import BrickState
from creme.creme_core.models import (
    CustomField,
    CustomFieldEnumValue,
    DeletionCommand,
    Job,
)
from creme.creme_core.views import generic
from creme.creme_core.views.bricks import (
    BricksReloading,
    BrickStateExtraDataSetting,
)
from creme.creme_core.views.generic.base import EntityCTypeRelatedMixin
from creme.creme_core.views.utils import json_update_from_widget_response

from .. import bricks
from ..constants import BRICK_STATE_HIDE_DELETED_CFIELDS
from ..forms import custom_field as cf_forms
from . import base

# logger = logging.getLogger(__name__)


class FirstCTypeCustomFieldCreation(base.ConfigModelCreation):
    model = CustomField
    # form_class = cf_forms.CustomFieldsCTAddForm
    form_class = cf_forms.FirstCustomFieldCreationForm
    title = _('New custom field configuration')


class CustomFieldCreation(EntityCTypeRelatedMixin,
                          base.ConfigModelCreation):
    model = CustomField
    form_class = cf_forms.CustomFieldCreationForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['ctype'] = self.get_ctype()

        return kwargs

    def get_title(self):
        return gettext('New custom field for «{model}»').format(
            model=self.get_ctype(),
        )


class Portal(generic.BricksView):
    template_name = 'creme_config/custom_field/portal.html'


class CustomFieldEdition(base.ConfigModelEdition):
    model = CustomField
    form_class = cf_forms.CustomFieldEditionForm
    pk_url_kwarg = 'field_id'

    def check_instance_permissions(self, instance, user):
        if instance.is_deleted:
            raise ConflictError(gettext('This custom field is deleted.'))


class CustomFieldDeletion(base.ConfigDeletion):
    id_arg = 'id'

    def perform_deletion(self, request):
        cfield = get_object_or_404(
            CustomField,
            id=utils.get_from_POST_or_404(request.POST, self.id_arg),
        )
        if cfield.is_deleted:
            times_used = cfield.value_class.objects.filter(custom_field=cfield).count()

            if times_used:
                raise ConflictError(
                    ngettext(
                        'This custom field is still used by {count} entity, '
                        'so it cannot be deleted.',
                        'This custom field is still used by {count} entities, '
                        'so it cannot be deleted.',
                        times_used
                    ).format(count=times_used)
                )

            cfield.delete()
        else:
            cfield.is_deleted = True
            cfield.save()


class CustomFieldRestoration(base.ConfigDeletion):
    id_arg = 'id'

    def perform_deletion(self, request):
        CustomField.objects.filter(
            id=utils.get_from_POST_or_404(request.POST, self.id_arg),
        ).update(is_deleted=False)


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


class BaseCustomEnumAdding(EnumMixin, base.ConfigModelEdition):
    model = CustomField
    pk_url_kwarg = 'field_id'

    def check_instance_permissions(self, instance, user):
        self.check_custom_field(instance)

        if instance.is_deleted:
            raise ConflictError(gettext('This custom field is deleted.'))


class FromWidgetCustomEnumAdding(BaseCustomEnumAdding):
    form_class = cf_forms.CustomEnumAddingForm
    submit_label = _('Add this new choice')

    def form_valid(self, form):
        super().form_valid(form=form)

        return json_update_from_widget_response(self.object)


class CustomEnumsAdding(BaseCustomEnumAdding):
    form_class = cf_forms.CustomEnumsAddingForm
    submit_label = _('Add these new choices')


class CustomEnumEdition(base.ConfigModelEdition):
    model = CustomFieldEnumValue
    pk_url_kwarg = 'enum_id'
    form_class = cf_forms.CustomEnumEditionForm

    def check_instance_permissions(self, instance, user):
        if instance.custom_field.is_deleted:
            raise ConflictError(gettext('This custom field is deleted.'))


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
        if instance.custom_field.is_deleted:
            raise ConflictError(gettext('This custom field is deleted.'))

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
        # context['custom_field'] = get_object_or_404(
        context[CustomEnumsDetail.context_object_name] = get_object_or_404(
            CustomField,
            pk=self.kwargs[self.pk_url_kwarg],
        )

        return context

    def get_brick_ids(self):
        return [bricks.CustomEnumsBrick.id_]


# class HideDeletedCustomFields(generic.CheckedView):
#     value_arg = 'value'
#     brick_cls = bricks.CustomFieldsBrick
#
#     def post(self, request, **kwargs):
#         value = utils.get_from_POST_or_404(
#             request.POST, key=self.value_arg,
#             cast=utils.bool_from_str_extended,
#         )
#
#         # NB: we can still have a race condition because we do not use
#         #     select_for_update ; but it's a state related one user & one brick,
#         #     so it would not be a real world problem.
#         for _i in range(10):
#             state = BrickState.objects.get_for_brick_id(
#                 brick_id=self.brick_cls.id_,
#                 user=request.user,
#             )
#
#             try:
#                 if state.set_extra_data(
#                     key=BRICK_STATE_HIDE_DELETED_CFIELDS,
#                     value=value,
#                 ):
#                     state.save()
#             except IntegrityError:
#                 logger.exception('Avoid a duplicate.')
#                 continue
#             else:
#                 break
#
#         return HttpResponse()
class HideDeletedCustomFields(BrickStateExtraDataSetting):
    brick_cls = bricks.CustomFieldsBrick
    data_key = BRICK_STATE_HIDE_DELETED_CFIELDS
