# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

from django.db import DatabaseError
from django.db.transaction import atomic
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
# from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _  # ugettext

# from formtools.wizard.views import SessionWizardView

from creme.creme_core.auth.decorators import _check_superuser  # login_required, superuser_required
from creme.creme_core.models import UserRole, SetCredentials, lock
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic
# from creme.creme_core.views.decorators import POST_only
# from creme.creme_core.views.generic.wizard import PopupWizardMixin

from ..forms import user_role as role_forms

logger = logging.getLogger(__name__)


class Portal(generic.BricksView):
    template_name = 'creme_config/user_role_portal.html'


# class RoleCreationWizard(PopupWizardMixin, SessionWizardView):
#     class _CredentialsStep(role_forms.UserRoleCredentialsStep):
#         step_submit_label = UserRole.save_label
#
#     form_list = (
#         role_forms.UserRoleAppsStep,
#         role_forms.UserRoleAdminAppsStep,
#         role_forms.UserRoleCreatableCTypesStep,
#         role_forms.UserRoleExportableCTypesStep,
#         _CredentialsStep,
#     )
#     template_name = 'creme_core/generics/blockform/add_wizard_popup.html'
#     wizard_title = UserRole.creation_label
#
#     def __init__(self, *args, **kwargs):
#         SessionWizardView.__init__(self, **kwargs)
#         self.role = UserRole()
#
#     @method_decorator(login_required)
#     def dispatch(self, *args, **kwargs):
#         _check_superuser(self.request.user)
#
#         return super().dispatch(*args, **kwargs)
#
#     def done(self, form_list, **kwargs):
#         form_iter = iter(form_list)
#
#         with atomic():
#             next(form_iter).partial_save()
#
#             for form in form_iter:
#                 form.save()
#
#         return HttpResponse()
#
#     def get_form_instance(self, step):
#         if step in {'0', '1', '2', '3'}:
#             return self.role
#
#     def get_form_kwargs(self, step):
#         kwargs = super().get_form_kwargs(step)
#
#         if step != '0':
#             kwargs['allowed_app_names'] = self.get_cleaned_data_for_step('0')['allowed_apps']
#
#         if step == '4':
#             kwargs['instance'] = self.role
#
#         return kwargs
class RoleCreationWizard(generic.CremeModelCreationWizardPopup):
    form_list = (
        role_forms.UserRoleAppsStep,
        role_forms.UserRoleAdminAppsStep,
        role_forms.UserRoleCreatableCTypesStep,
        role_forms.UserRoleExportableCTypesStep,
        role_forms.UserRoleCredentialsGeneralStep,
        role_forms.UserRoleCredentialsFilterStep,
    )
    model = UserRole
    # permissions = 'creme_core.can_admin'  # TODO: 'superuser' perm ??

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.role = UserRole()
        self.set_cred = SetCredentials()

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)
        _check_superuser(user)  # TODO: set public ?

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


# class RoleEditionWizard(PopupWizardMixin, SessionWizardView):
#     class _ExportableCTypesStep(role_forms.UserRoleExportableCTypesStep):
#         step_submit_label = _('Save the modifications')
#
#     form_list = (role_forms.UserRoleAppsStep,
#                  role_forms.UserRoleAdminAppsStep,
#                  role_forms.UserRoleCreatableCTypesStep,
#                  _ExportableCTypesStep,
#                  )
#
#     template_name = 'creme_core/generics/blockform/edit_wizard_popup.html'
#     wizard_title = 'Edit role'  # Overloaded in dispatch()
#
#     @method_decorator(login_required)
#     def dispatch(self, *args, **kwargs):
#         _check_superuser(self.request.user)
#
#         self.role = role = get_object_or_404(UserRole, pk=kwargs['role_id'])
#         self.wizard_title = ugettext('Edit «{}»').format(role)
#
#         return super().dispatch(*args, **kwargs)
#
#     def done(self, form_list, **kwargs):
#         form_iter = iter(form_list)
#
#         with atomic():
#             next(form_iter).partial_save()
#
#             for form in form_iter:
#                 form.save()
#
#         return HttpResponse()
#
#     def get_form_instance(self, step):
#         return self.role
#
#     def get_form_kwargs(self, step):
#         kwargs = super().get_form_kwargs(step)
#
#         if step != '0':
#             kwargs['allowed_app_names'] = self.get_cleaned_data_for_step('0')['allowed_apps']
#
#         return kwargs
class RoleEditionWizard(generic.CremeModelEditionWizardPopup):
    model = UserRole
    pk_url_kwarg = 'role_id'
    # permission = 'creme_core.can_admin'  # TODO: 'superuser' perm

    form_list = (
        role_forms.UserRoleAppsStep,
        role_forms.UserRoleAdminAppsStep,
        role_forms.UserRoleCreatableCTypesStep,
        role_forms.UserRoleExportableCTypesStep,
    )

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)
        _check_superuser(user)  # TODO: set public ?

    def done_save(self, form_list):
        for form in form_list:
            form.save()


# TODO: merge with RoleDeletion
class BaseRoleEdition(generic.CremeModelEditionPopup):
    model = UserRole
    pk_url_kwarg = 'role_id'

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)
        _check_superuser(user)


# class CredentialsAdding(BaseRoleEdition):
#     form_class = role_forms.AddCredentialsForm
#     title = _('Add credentials to «{object}»')
#     submit_label = _('Add the credentials')
class CredentialsAddingWizard(generic.CremeModelEditionWizardPopup):
    model = UserRole
    pk_url_kwarg = 'role_id'

    title = _('Add credentials to «{object}»')

    class LastStep(role_forms.CredentialsFilterStep):
        step_submit_label = _('Add the credentials')

    form_list = (
        role_forms.CredentialsGeneralStep,
        LastStep,
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.credentials = SetCredentials(role=self.object)

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)
        _check_superuser(user)  # TODO: permissions = "*super*"

    def done_save(self, form_list):
        for form in form_list:
            form.save()

    def get_form_instance(self, step):
        creds = self.credentials
        creds.role = self.object

        return creds


# class CredentialsEdition(generic.CremeModelEditionPopup):
#     model = SetCredentials
#     form_class = role_forms.EditCredentialsForm
#     pk_url_kwarg = 'cred_id'
#     title = _('Edit credentials for «{role}»')
#
#     def check_view_permissions(self, user):
#         super().check_view_permissions(user=user)
#         _check_superuser(user)
#
#     def get_title_format_data(self):
#         data = super().get_title_format_data()
#         data['role'] = self.object.role
#
#         return data
class CredentialsEditionWizard(generic.CremeModelEditionWizardPopup):
    model = SetCredentials
    pk_url_kwarg = 'cred_id'

    title = _('Edit credentials for «{role}»')

    form_list = (
        role_forms.CredentialsGeneralStep,
        role_forms.CredentialsFilterStep,
    )

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)
        _check_superuser(user)  # TODO: permissions = "*super*"

    def done_save(self, form_list):
        for form in form_list:
            form.save()

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['role'] = self.object.role

        return data


# @login_required
# @superuser_required
# @POST_only
# def delete_credentials(request):
#     get_object_or_404(SetCredentials, pk=get_from_POST_or_404(request.POST, 'id')).delete()
#     return HttpResponse()
class CredentialsDeletion(generic.CheckedView):
    creds_id_arg = 'id'

    # TODO: factorise/ "*super*" permission
    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)
        _check_superuser(user)

    @atomic
    def post(self, request, *args, **kwargs):
        get_object_or_404(
            SetCredentials,
            id=get_from_POST_or_404(request.POST, self.creds_id_arg),
        ).delete()

        return HttpResponse()


class RoleDeletion(BaseRoleEdition):
    form_class = role_forms.UserRoleDeleteForm
    template_name = 'creme_core/generics/blockform/delete-popup.html'
    title = _('Delete role «{object}»')
    submit_label = _('Delete the role')  # TODO: deletion_label ?

    lock_name = 'creme_config-role_transfer'

    def post(self, *args, **kwargs):
        try:
            # We create the lock out-of the super-post() transaction
            with lock.MutexAutoLock(self.lock_name):
                return super().post(*args, **kwargs)
        except (DatabaseError, lock.MutexLockedException) as e:
            logger.exception('RoleDeletion: an error occurred')

            return HttpResponse(
                _('You cannot delete this role. [original error: {}]').format(e),
                status=400,
            )
