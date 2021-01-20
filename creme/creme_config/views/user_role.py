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

from django.contrib.contenttypes.models import ContentType
from django.db.transaction import atomic
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.auth import SUPERUSER_PERM
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import (
    DeletionCommand,
    Job,
    SetCredentials,
    UserRole,
)
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic

from ..forms import user_role as role_forms

logger = logging.getLogger(__name__)


class Portal(generic.BricksView):
    template_name = 'creme_config/portals/user-role.html'


class RoleCreationWizard(generic.CremeModelCreationWizardPopup):
    form_list = [
        role_forms.UserRoleAppsStep,
        role_forms.UserRoleAdminAppsStep,
        role_forms.UserRoleCreatableCTypesStep,
        role_forms.UserRoleExportableCTypesStep,
        role_forms.UserRoleCredentialsGeneralStep,
        role_forms.UserRoleCredentialsFilterStep,
    ]
    model = UserRole
    permissions = SUPERUSER_PERM

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.role = UserRole()
        self.set_cred = SetCredentials()

    def done_save(self, form_list):
        for form in form_list:
            form.save()

    def get_form_instance(self, step):
        model = self.form_list.get(step)._meta.model

        if issubclass(model, UserRole):
            instance = self.role
        else:
            assert issubclass(model, SetCredentials)
            instance = self.set_cred

        # We fill the instance with the previous step (so recursively all previous should be used)
        self.validate_previous_steps(step)

        return instance

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)

        model = self.form_list.get(step)._meta.model  # TODO: factorise ?
        if issubclass(model, SetCredentials):
            kwargs['role'] = self.role

        return kwargs


class RoleEditionWizard(generic.CremeModelEditionWizardPopup):
    model = UserRole
    pk_url_kwarg = 'role_id'
    permissions = SUPERUSER_PERM

    form_list = [
        role_forms.UserRoleAppsStep,
        role_forms.UserRoleAdminAppsStep,
        role_forms.UserRoleCreatableCTypesStep,
        role_forms.UserRoleExportableCTypesStep,
    ]

    def done_save(self, form_list):
        for form in form_list:
            form.save()


class CredentialsAddingWizard(generic.CremeModelEditionWizardPopup):
    model = UserRole
    pk_url_kwarg = 'role_id'
    permissions = SUPERUSER_PERM
    title = _('Add credentials to «{object}»')

    class LastStep(role_forms.CredentialsFilterStep):
        step_submit_label = _('Add the credentials')

    form_list = [
        role_forms.CredentialsGeneralStep,
        LastStep,
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.credentials = SetCredentials(role=self.object)

    def done_save(self, form_list):
        for form in form_list:
            form.save()

    def get_form_instance(self, step):
        creds = self.credentials
        creds.role = self.object

        return creds


class CredentialsEditionWizard(generic.CremeModelEditionWizardPopup):
    model = SetCredentials
    pk_url_kwarg = 'cred_id'
    permissions = SUPERUSER_PERM
    title = _('Edit credentials for «{role}»')

    form_list = [
        role_forms.CredentialsGeneralStep,
        role_forms.CredentialsFilterStep,
    ]

    def done_save(self, form_list):
        for form in form_list:
            form.save()

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['role'] = self.object.role

        return data


class CredentialsDeletion(generic.CheckedView):
    creds_id_arg = 'id'
    permissions = SUPERUSER_PERM

    @atomic
    def post(self, request, *args, **kwargs):
        get_object_or_404(
            SetCredentials,
            id=get_from_POST_or_404(request.POST, self.creds_id_arg),
        ).delete()

        return HttpResponse()


class RoleDeletion(generic.CremeModelEditionPopup):
    model = UserRole
    pk_url_kwarg = 'role_id'
    permissions = SUPERUSER_PERM
    form_class = role_forms.UserRoleDeletionForm
    template_name = 'creme_core/generics/blockform/delete-popup.html'
    job_template_name = 'creme_config/deletion-job-popup.html'
    title = _('Delete role «{object}»')
    submit_label = _('Delete the role')  # TODO: deletion_label ?

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
                raise ConflictError(gettext('A deletion process for a role already exists.'))

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
        kwargs['role_to_delete'] = self.object

        return kwargs
