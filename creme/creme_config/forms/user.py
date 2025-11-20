################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from collections import defaultdict

from django import forms
from django.contrib.auth import forms as auth_forms
from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_config import notification
from creme.creme_core.constants import UUID_CHANNEL_ADMIN
from creme.creme_core.forms import CremeForm, CremeModelForm
from creme.creme_core.models import Notification  # UserRole
from creme.creme_core.models.fields import CremeUserForeignKey

CremeUser = get_user_model()


# TODO: inherit from django.contrib.auth.forms.(Base)UserCreationForm
#       => we need a Mixin to initialize the user in fields (like HookableForm)
class UserCreationForm(CremeModelForm):
    error_messages = {
        'password_mismatch': auth_forms.UserCreationForm.error_messages['password_mismatch'],
    }

    password_1 = forms.CharField(
        label=_('Password'),
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text=password_validation.password_validators_help_text_html(),
    )
    password_2 = forms.CharField(
        label=_('Confirm password'),
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text=_('Enter the same password as before, for verification.'),
    )

    # role = forms.ModelChoiceField(
    #     label=_('Role'), required=False, queryset=UserRole.objects.all(),
    # )

    class Meta:
        model = CremeUser
        fields = (
            'username', 'last_name', 'first_name', 'email', 'displayed_name',
            # 'role',
            'roles',
        )
        field_classes = {'username': auth_forms.UsernameField}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # # NB: browser can ignore <em> tag in <option>...
        # self.fields['role'].empty_label = '*{}*'.format(gettext('Superuser'))

        roles_f = self.fields['roles']
        roles_f.queryset = roles_f.queryset.filter(deactivated_on=None)

    # Derived from django.contrib.auth.forms.UserCreationForm
    def clean_username(self):
        """Reject usernames that differ only in case."""
        username = self.cleaned_data.get('username')
        if (
            username
            and self._meta.model.objects.filter(username__iexact=username).exists()
        ):
            raise ValidationError(self.instance.unique_error_message(
                model_class=self._meta.model, unique_check=['username'],
            ))

        return username

    # Copied from django.contrib.auth.forms.UserCreationForm
    def clean_password_2(self):
        get_data = self.cleaned_data.get
        password1 = get_data('password_1')
        password2 = get_data('password_2')

        if password1 and password2 and password1 != password2:
            raise ValidationError(
                self.error_messages['password_mismatch'],
                code='password_mismatch',
            )

        return password2

    def clean_roles(self):
        roles = self.cleaned_data.get('roles')

        if roles:
            self.instance.role = roles[0]
        else:
            self.instance.is_superuser = True

        return roles

    def _post_clean(self):
        super()._post_clean()
        # NB: some validators (like the "similarity" one) need 'self.instance' to
        #     be updated with POSTed data, so we do not call 'validate_password()'
        #     in 'clean_password_2()'
        password = self.cleaned_data.get('password_2')
        if password:
            try:
                password_validation.validate_password(password, self.instance)
            except ValidationError as e:
                self.add_error('password_2', e)

    def save(self, *args, **kwargs):
        instance = self.instance
        # instance.is_superuser = (instance.role is None)
        instance.set_password(self.cleaned_data['password_1'])
        super().save(*args, **kwargs)

        if instance.role:
            instance.roles.add(instance.role)

        return instance


# TODO: factorise with UserCreationForm
class UserEditionForm(CremeModelForm):
    # role = forms.ModelChoiceField(
    #     label=_('Role'), queryset=UserRole.objects.all(), required=False,
    # )

    class Meta:
        model = CremeUser
        fields = (
            'first_name', 'last_name', 'email', 'displayed_name',
            # 'role', 'is_superuser'
            'roles',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # # NB: browser can ignore <em> tag in <option>...
        # self.fields['role'].empty_label = '*{}*'.format(gettext('Superuser'))

        roles_f = self.fields['roles']
        roles_f.queryset = roles_f.queryset.filter(
            Q(deactivated_on=None)
            | Q(id__in=self.instance.roles.values_list('id', flat=True))
        )

    # def clean(self):
    #     cdata = super().clean()
    #
    #     if not self._errors:
    #         instance = self.instance
    #         instance.role = role = cdata['role']
    #         instance.is_superuser = (role is None)
    #
    #     return cdata
    def clean_roles(self):
        roles = self.cleaned_data.get('roles')
        instance = self.instance

        if roles:
            if all(role.deactivated_on for role in roles):
                raise ValidationError(gettext('Select at least one enabled role.'))

            instance.is_superuser = False

            # We keep the current active role if possible
            if instance.role not in roles:
                instance.role = roles[0]
        else:
            instance.is_superuser = True
            instance.role = None

        return roles

    def save(self, *args, **kwargs):
        instance = self.instance
        roles = self.cleaned_data['roles']
        if instance.role and instance.role.deactivated_on:
            # NB: we are sure there is at least one active role (see clean_roles())
            instance.role = next(role for role in roles if role.deactivated_on is None)
            Notification.objects.send(
                users=[instance], channel=UUID_CHANNEL_ADMIN,
                content=notification.RoleSwitchContent(),
            )

        super().save(*args, **kwargs)
        instance.roles.set(roles)

        return instance


# NB: we cannot use django.contrib.auth.forms.AdminPasswordChangeForm, because
#     it defines a 'user' attribute like us (but it corresponds to our
#     'user2edit' one, not our 'user' one)
class UserPasswordChangeForm(CremeForm):
    error_messages = {
        'password_mismatch': auth_forms.SetPasswordForm.error_messages['password_mismatch'],
        'password_incorrect': auth_forms.PasswordChangeForm.error_messages['password_incorrect'],
    }

    old_password = forms.CharField(
        label=_('Your old password'),
        strip=False,
        widget=forms.PasswordInput(
            attrs={'autocomplete': 'current-password', 'autofocus': True},
        ),
    )
    password_1 = forms.CharField(
        label=_('New password'),
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text=password_validation.password_validators_help_text_html(),
    )
    password_2 = forms.CharField(
        label=_('New password confirmation'),
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text=_('Enter the same password as before, for verification.'),
    )

    def __init__(self, *args, **kwargs):
        self.user2edit = user2edit = kwargs.pop('instance')
        super().__init__(*args, **kwargs)

        if self.user != user2edit:
            fields = self.fields
            fields['old_password'].label = _('Your password')
            fields['password_1'].label = gettext(
                'New password for «{user}»'
            ).format(user=user2edit)

    def clean_old_password(self):
        old_password = self.cleaned_data["old_password"]

        if not self.user.check_password(old_password):
            raise ValidationError(
                self.error_messages['password_incorrect'],
                code='password_incorrect',
            )

        return old_password

    def clean_password_2(self):
        data = self.data
        pw2  = data['password_2']

        if data['password_1'] != pw2:
            raise ValidationError(
                self.error_messages['password_mismatch'], code='password_mismatch',
            )

        password_validation.validate_password(pw2, self.user2edit)

        return pw2

    def save(self):
        user = self.user2edit
        user.set_password(self.cleaned_data.get('password_1'))
        user.save()

        if self.user != user:
            Notification.objects.send(
                users=[user], channel=UUID_CHANNEL_ADMIN,
                content=notification.PasswordChangeContent(),
            )


class _TeamForm(CremeModelForm):
    teammates = forms.ModelMultipleChoiceField(
        queryset=CremeUser.objects.filter(is_team=False, is_staff=False),
        label=_('Teammates'), required=False,
    )

    class Meta:
        model = CremeUser
        fields = ('username',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = gettext('Team name')
        self.instance.is_team = True  # For correct cleaning rules

    def save(self, *args, **kwargs):
        team = super().save(*args, **kwargs)
        team.teammates = self.cleaned_data['teammates']

        return team


class TeamCreationForm(_TeamForm):
    pass


class TeamEditionForm(_TeamForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['teammates'].initial = self.instance.teammates


class UserAssignationForm(CremeForm):
    to_user = forms.ModelChoiceField(
        label=_('Choose a user to transfer to'),
        queryset=CremeUser.objects.none(),
    )

    def __init__(self, user, instance, *args, **kwargs):
        """Forms which assigns the fields with type CremeUserForeignKey
        referencing a given user A to another user B, then deletes A.

        @param user: User who is logged & makes the deletion.
        @param instance: Instance of contrib.auth.get_user_model() to delete.
        """
        super().__init__(user, *args, **kwargs)
        self.user_to_delete = instance

        users = CremeUser.objects.exclude(pk=instance.pk).exclude(is_staff=True)
        choices = defaultdict(list)
        for user in users:
            choices[user.is_team].append((user.id, str(user)))

        to_user = self.fields['to_user']
        to_user.queryset = users
        to_user.choices = [
            (gettext('Users'), choices[False]),
            (gettext('Teams'), choices[True]),
        ]

    def save(self, *args, **kwargs):
        CremeUserForeignKey._TRANSFER_TO_USER = self.cleaned_data['to_user']

        try:
            self.user_to_delete.delete()
        finally:
            CremeUserForeignKey._TRANSFER_TO_USER = None
