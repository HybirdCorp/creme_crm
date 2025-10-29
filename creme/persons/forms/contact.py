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

from django import forms
from django.contrib.auth import forms as auth_forms
from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError
from django.db.transaction import atomic
# from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

# from creme.creme_core.models import UserRole
from creme.creme_core.forms import CremeEntityForm, CremeModelForm


class BaseContactCustomForm(CremeEntityForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.is_user_id:
            get_field = self.fields.get

            for field_name in ('first_name', 'email'):
                field = get_field(field_name)
                if field is not None:
                    field.required = True


# TODO: factorise with <creme.creme_config.forms.user.UserCreationForm>?
class UserFromContactCreationForm(CremeModelForm):
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
        model = get_user_model()
        # fields = ('username', 'first_name', 'email', 'displayed_name', 'role')
        fields = ('username', 'first_name', 'email', 'displayed_name', 'roles')
        field_classes = {'username': auth_forms.UsernameField}

    def __init__(self, contact, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.contact = contact
        fields = self.fields

        # # NB: browser can ignore <em> tag in <option>...
        # fields['role'].empty_label = '*{}*'.format(gettext('Superuser'))

        instance = self.instance
        instance.last_name = contact.last_name

        if contact.first_name:
            instance.first_name = contact.first_name
            del fields['first_name']
        else:
            first_name_f = fields['first_name']
            first_name_f.required = True
            first_name_f.help_text = _('The first name of the Contact will be updated.')

        email_f = fields['email']
        email_f.required = True
        email = contact.email
        if email:
            if type(instance).objects.filter(email=email):
                email_f.help_text = _(
                    'BEWARE: the email of the Contact is already used by a '
                    'user & will be updated.'
                )
            else:
                email_f.initial = email
                email_f.help_text = _(
                    'The email of the Contact will be updated if you change it.'
                )
        else:
            email_f.help_text = _('The email of the Contact will be updated.')

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

    @atomic
    def save(self, *args, **kwargs):
        instance = self.instance

        instance.is_superuser = (instance.role is None)
        instance.set_password(self.cleaned_data['password_1'])
        # TODO: Contact.disable_user_syn(user)?
        instance._disable_sync_with_contact = True

        super().save(*args, **kwargs)

        contact = self.contact
        contact.is_user = instance
        contact.first_name = instance.first_name
        contact.email = instance.email
        contact.save()

        return instance
