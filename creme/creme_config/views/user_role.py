# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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

import warnings

from django.db.transaction import atomic
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _, ugettext

from formtools.wizard.views import SessionWizardView

from creme.creme_core.auth.decorators import login_required, superuser_required, _check_superuser
from creme.creme_core.models import UserRole, SetCredentials
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views.generic import add_model_with_popup, edit_model_with_popup, inner_popup
from creme.creme_core.views.decorators import POST_only
from creme.creme_core.views.generic.wizard import PopupWizardMixin

from ..forms.user_role import (UserRoleCreateForm, UserRoleEditForm,
        AddCredentialsForm, EditCredentialsForm, UserRoleDeleteForm)
from ..forms import user_role as user_role_forms


@login_required
@superuser_required
def add(request):
    warnings.warn("creme_config/role/add/ is now deprecated. "
                  "Use creme_config/role/wizard view instead.",
                  DeprecationWarning
                 )

    return add_model_with_popup(request, UserRoleCreateForm, _(u'New role'),
                                # submit_label=_('Save the role'),
                                submit_label=UserRole.save_label,
                               )


class UserRoleCreationWizard(PopupWizardMixin, SessionWizardView):
    class _CredentialsStep(user_role_forms.UserRoleCredentialsStep):
        # step_submit_label = _('Save the role')
        step_submit_label = UserRole.save_label

    form_list = (user_role_forms.UserRoleAppsStep,
                 user_role_forms.UserRoleAdminAppsStep,
                 user_role_forms.UserRoleCreatableCTypesStep,
                 user_role_forms.UserRoleExportableCTypesStep,
                 _CredentialsStep,
                )
    # wizard_title = _(u'New role')
    wizard_title = UserRole.creation_label
    # permission = 'creme_core.can_admin'  # TODO: 'superuser' perm ??

    def __init__(self, *args, **kwargs):
        SessionWizardView.__init__(self, **kwargs)
        self.role = UserRole()

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        _check_superuser(self.request.user)   # TODO: set public ?

        return super(UserRoleCreationWizard, self).dispatch(*args, **kwargs)

    def done(self, form_list, **kwargs):
        with atomic():
            form_list[0].partial_save()
            form_list[1].save()

            form_list[2].save()
            form_list[3].save()

            form_list[4].save()

        return HttpResponse('', content_type='text/javascript')

    def get_form_instance(self, step):
        if step in ('0', '1', '2', '3'):
            return self.role

    def get_form_kwargs(self, step):
        kwargs = super(UserRoleCreationWizard, self).get_form_kwargs(step)

        if step != '0':
            kwargs['allowed_app_names'] = self.get_cleaned_data_for_step('0')['allowed_apps']

        if step == '4':
            kwargs['role'] = self.role

        return kwargs


class UserRoleEditionWizard(PopupWizardMixin, SessionWizardView):
    class _ExportableCTypesStep(user_role_forms.UserRoleExportableCTypesStep):
        step_submit_label = _('Save the modifications')

    form_list = (user_role_forms.UserRoleAppsStep,
                 user_role_forms.UserRoleAdminAppsStep,
                 user_role_forms.UserRoleCreatableCTypesStep,
                 _ExportableCTypesStep,
                )

    wizard_title = u'Edit role'  # Overloaded in dispatch()
    # permission = 'creme_core.can_admin'  # TODO: 'superuser' perm ??

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        _check_superuser(self.request.user)  # TODO: set public ?

        self.role = role = get_object_or_404(UserRole, pk=kwargs['role_id'])
        self.wizard_title = ugettext(u'Edit «%s»') % role

        return super(UserRoleEditionWizard, self).dispatch(*args, **kwargs)

    def done(self, form_list, **kwargs):
        with atomic():
            form_list[0].partial_save()
            form_list[1].save()

            form_list[2].save()
            form_list[3].save()

        return HttpResponse('', content_type='text/javascript')

    def get_form_instance(self, step):
        return self.role

    def get_form_kwargs(self, step):
        kwargs = super(UserRoleEditionWizard, self).get_form_kwargs(step)

        if step != '0':
            kwargs['allowed_app_names'] = self.get_cleaned_data_for_step('0')['allowed_apps']

        return kwargs


@login_required
@superuser_required
def edit(request, role_id):
    warnings.warn("creme_config/role/edit/{{role.id}} is now deprecated. "
                  "Use creme_config/role/wizard/{{role.id}} view instead.",
                  DeprecationWarning
                 )

    return edit_model_with_popup(request, {'pk': role_id}, UserRole, UserRoleEditForm)


@login_required
@superuser_required
def add_credentials(request, role_id):
    role = get_object_or_404(UserRole, pk=role_id)

    if request.method == 'POST':
        add_form = AddCredentialsForm(role, user=request.user, data=request.POST)

        if add_form.is_valid():
            add_form.save()
    else:
        add_form = AddCredentialsForm(role, user=request.user)

    return inner_popup(request, 'creme_core/generics/blockform/edit_popup.html',
                       {'form':  add_form,
                        'title': _(u'Add credentials to «%s»') % role,
                        'submit_label': _('Add the credentials'),
                       },
                       is_valid=add_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )


# TODO: edit_model_with_popup  => improve title creation
@login_required
@superuser_required
def edit_credentials(request, cred_id):
    creds = get_object_or_404(SetCredentials, pk=cred_id)

    if request.method == 'POST':
        edit_form = EditCredentialsForm(instance=creds, user=request.user, data=request.POST)

        if edit_form.is_valid():
            edit_form.save()
    else:
        edit_form = EditCredentialsForm(instance=creds, user=request.user)

    return inner_popup(request, 'creme_core/generics/blockform/edit_popup.html',
                       {'form':  edit_form,
                        'title': _(u'Edit credentials for «%s»') % creds.role,
                        'submit_label': _('Save the modifications'),
                       },
                       is_valid=edit_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )


@login_required
@superuser_required
@POST_only
def delete_credentials(request):
    get_object_or_404(SetCredentials, pk=get_from_POST_or_404(request.POST, 'id')).delete()
    return HttpResponse()


@login_required
def portal(request):
    return render(request, 'creme_config/user_role_portal.html')


@login_required
@superuser_required
def delete(request, role_id):
    role = get_object_or_404(UserRole, pk=role_id)

    return add_model_with_popup(request, UserRoleDeleteForm,
                                _(u'Delete role «%s»') % role,
                                initial={'role_to_delete': role},
                                submit_label=_('Delete the role'),
                               )
