################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2022-2025  Hybird
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

import django.contrib.auth.views as auth_views
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db.transaction import atomic
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils.safestring import mark_safe
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core import get_world_settings_model

from ..core.exceptions import ConflictError
from ..models import UserRole
from . import generic


# User -------------------------------------------------------------------------
class RoleSwitch(generic.CheckedView):
    user_id_url_kwarg = 'user_id'
    role_id_url_kwarg = 'role_id'

    @atomic
    def post(self, request, *args, **kwargs):
        user = get_object_or_404(
            get_user_model().objects.select_for_update(),
            id=kwargs[self.user_id_url_kwarg],
        )
        if user.is_superuser:
            raise ConflictError(gettext('Superusers cannot switch their role'))

        role_id = kwargs[self.role_id_url_kwarg]

        if role_id != user.role_id:
            role = get_object_or_404(UserRole, id=role_id)

            if not user.roles.filter(id=role.id).exists():
                raise ConflictError(gettext('This role is not available for you'))

            user.role = role
            user.save()

        return HttpResponse()


# Password ---------------------------------------------------------------------
class PasswordReset(generic.base.SubmittableMixin, auth_views.PasswordResetView):
    extra_email_context = {
        'software': settings.SOFTWARE_LABEL,
    }
    template_name = 'creme_core/auth/password_reset/reset-email.html'
    subject_template_name = 'creme_core/auth/password_reset/email/subject.txt'
    email_template_name = 'creme_core/auth/password_reset/email/body.txt'
    # html_email_template_name = None  # Set to get an HTML email
    # from_email = 'noreply@mycompagny.org'  # NB: settings.DEFAULT_FROM_EMAIL used by default
    success_url = reverse_lazy('creme_core__password_reset_done')
    title = _('Reset your password (Step 1/4)')
    submit_label = _('Send me instructions')

    def dispatch(self, *args, **kwargs):
        if not get_world_settings_model().objects.instance().password_reset_enabled:
            raise PermissionDenied(
                gettext('You are not allowed to use the «Lost password» feature.')
            )
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['submit_label'] = self.get_submit_label()

        return context


class PasswordResetDone(auth_views.PasswordResetDoneView):
    template_name = 'creme_core/auth/password_reset/done.html'
    title = _('Reset your password (Step 2/4)')


class PasswordResetConfirm(generic.base.SubmittableMixin,
                           auth_views.PasswordResetConfirmView):
    template_name = 'creme_core/auth/password_reset/confirm.html'
    success_url = reverse_lazy('creme_core__password_reset_complete')
    title = _('Reset your password (Step 3/4)')
    submit_label = _('Save the new password')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['submit_label'] = self.get_submit_label()

        return context


class PasswordResetComplete(auth_views.PasswordResetCompleteView):
    template_name = 'creme_core/auth/password_reset/complete.html'


class OwnPasswordChange(generic.base.CancellableMixin,
                        generic.base.SubmittableMixin,
                        auth_views.PasswordChangeView):
    template_name = 'creme_core/generics/form/edit.html'
    success_url = reverse_lazy('creme_core__own_password_change_done')

    title = _('Change your password')
    submit_label = _('Save the new password')

    def dispatch(self, *args, **kwargs):
        if not get_world_settings_model().objects.instance().password_change_enabled:
            raise PermissionDenied(
                gettext('You are not allowed to change your password.')
            )
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['submit_label'] = self.get_submit_label()
        context['cancel_url'] = self.get_cancel_url()

        if get_world_settings_model().objects.instance().password_reset_enabled:
            context['help_message'] = mark_safe(
                gettext(
                    'You lost your password? <a href="{url}">You can reset it</a>'
                ).format(url=reverse('creme_core__reset_password'))
            )

        return context


class OwnPasswordChangeDone(auth_views.PasswordChangeDoneView):
    template_name = 'creme_core/info.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['information_messages'] = [
            gettext('Use your new password the next time you want to login.'),
        ]

        return context
