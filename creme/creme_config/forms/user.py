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

# import warnings
from collections import defaultdict

from django.contrib.auth import forms as auth_forms
from django.contrib.auth import get_user_model, password_validation
from django.forms import CharField, ModelChoiceField, ModelMultipleChoiceField
from django.forms.utils import ValidationError
from django.forms.widgets import PasswordInput
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms import CremeForm, CremeModelForm
from creme.creme_core.models import UserRole
from creme.creme_core.models.fields import CremeUserForeignKey

CremeUser = get_user_model()


# def _password_validators_help_text_html(password_validators=None):
#     warnings.warn(
#         'creme_config.forms.user._password_validators_help_text_html() is deprecated.',
#         DeprecationWarning,
#     )
#
#     from django.utils.html import format_html, format_html_join
#
#     help_texts = password_validation.password_validators_help_texts(password_validators)
#
#     if not help_texts:
#         return ''
#
#     return format_html(
#         '<ul>{}</ul>',
#         format_html_join('', '<li>{}</li>', ((text,) for text in help_texts))
#     )


# TODO: inherit from django.contrib.auth.forms.UserCreationForm
#       => we need a Mixin to initialize the user in fields  (like HookableForm)
class UserAddForm(CremeModelForm):
    # Copied from django.contrib.auth.forms.UserCreationForm
    error_messages = {
        # 'password_mismatch': _("The two password fields didn't match."),
        'password_mismatch': auth_forms.UserCreationForm.error_messages['password_mismatch'],
    }

    password_1 = CharField(
        label=_('Password'),
        strip=False,
        widget=PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text=password_validation.password_validators_help_text_html(),
    )
    password_2 = CharField(
        label=_('Confirm password'),
        strip=False,
        widget=PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text=_('Enter the same password as before, for verification.'),
    )

    role = ModelChoiceField(
        label=_('Role'), required=False, queryset=UserRole.objects.all(),
    )

    class Meta:
        model = CremeUser
        fields = ('username', 'last_name', 'first_name', 'email', 'role')  # 'is_superuser'
        field_classes = {'username': auth_forms.UsernameField}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # NB: browser can ignore <em> tag in <option>...
        self.fields['role'].empty_label = '*{}*'.format(gettext('Superuser'))

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
        # TODO: remove field CremeUser.is_superuser ??
        instance.is_superuser = (instance.role is None)
        instance.set_password(self.cleaned_data['password_1'])

        return super().save(*args, **kwargs)


# TODO: factorise with UserAddForm
class UserEditForm(CremeModelForm):
    role = ModelChoiceField(
        label=_('Role'), queryset=UserRole.objects.all(), required=False,
    )

    class Meta:
        model = CremeUser
        fields = ('first_name', 'last_name', 'email', 'role')  # 'is_superuser'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # NB: browser can ignore <em> tag in <option>...
        self.fields['role'].empty_label = '*{}*'.format(gettext('Superuser'))

    def save(self, *args, **kwargs):
        instance = self.instance
        # NB: needed with django 1.8 when we reset to 'None'
        #     (the value seems skipped) => is it a bug ??
        instance.role = role = self.cleaned_data['role']
        instance.is_superuser = (role is None)

        return super().save(*args, **kwargs)


# NB: we cannot use django.contrib.auth.forms.AdminPasswordChangeForm, because it defines a 'user'
#     attribute like us (but it correspond to our 'user2edit' one, not our 'user' one)
class UserChangePwForm(CremeForm):
    error_messages = {
        # 'password_mismatch': _("The two password fields didn't match."),
        'password_mismatch': auth_forms.SetPasswordForm.error_messages['password_mismatch'],
    }

    password_1 = CharField(
        label=_('Password'),
        strip=False,
        widget=PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text=password_validation.password_validators_help_text_html(),
    )
    password_2 = CharField(
        label=_('Password (again)'),
        strip=False,
        widget=PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text=_('Enter the same password as before, for verification.'),
    )

    def __init__(self, *args, **kwargs):
        self.user2edit = kwargs.pop('instance')
        super().__init__(*args, **kwargs)

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


class TeamCreateForm(CremeModelForm):
    teammates = ModelMultipleChoiceField(
        queryset=CremeUser.objects.filter(is_team=False, is_staff=False),
        label=_('Teammates'), required=False,
    )

    class Meta:
        model = CremeUser
        fields = ('username',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = gettext('Team name')

    def save(self, *args, **kwargs):
        team = self.instance
        team.is_team = True
        super().save(*args, **kwargs)

        team.teammates = self.cleaned_data['teammates']

        return team


class TeamEditForm(TeamCreateForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['teammates'].initial = self.instance.teammates


class UserAssignationForm(CremeForm):
    to_user = ModelChoiceField(
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
