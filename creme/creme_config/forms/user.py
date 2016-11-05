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

from collections import defaultdict

from django.contrib.auth import get_user_model
from django.forms import CharField, ModelChoiceField, ModelMultipleChoiceField, RegexField
from django.forms.utils import ValidationError
from django.forms.widgets import PasswordInput
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.forms import CremeForm, CremeModelForm
# from creme.creme_core.forms.widgets import UnorderedMultipleChoiceWidget
from creme.creme_core.models import UserRole, Mutex
from creme.creme_core.models.fields import CremeUserForeignKey


CremeUser = get_user_model()

# TODO: inherit from django.contrib.auth.forms.UserCreationForm
class UserAddForm(CremeModelForm):
    # NB: field copied from django.contrib.auth.forms.UserCreationForm
    username = RegexField(label=_("Username"), max_length=30, regex=r'^[\w.@+-]+$',
                          help_text=_("Required. 30 characters or fewer. Letters, "
                                      "digits and @/./+/-/_ only."
                                     ),
                          error_messages={'invalid': _("This value may contain only letters, "
                                                       "numbers and @/./+/-/_ characters."
                                                      ),
                                         },
                         )
    password_1   = CharField(label=_('Password'), min_length=6, widget=PasswordInput())
    password_2   = CharField(label=_('Confirm password'), min_length=6, widget=PasswordInput())
    role         = ModelChoiceField(label=_('Role'), required=False,
                                    queryset=UserRole.objects.all(),
                                   )


    class Meta:
        model = CremeUser
        fields = ('username', 'last_name', 'first_name', 'email', 'role') # 'is_superuser'

    def __init__(self, *args, **kwargs):
        super(UserAddForm, self).__init__(*args, **kwargs)

        # NB: browser can ignore <em> tag in <option>...
        self.fields['role'].empty_label = u'*%s*' % ugettext(u'Superuser')

    def clean(self):
        cleaned = super(UserAddForm, self).clean()

        if not self._errors and cleaned['password_1'] != cleaned['password_2']:
            self.add_error('password_2', _(u'Passwords are different'))

        return cleaned

    def save(self, *args, **kwargs):
        instance = self.instance
        instance.is_superuser = (instance.role is None)  # TODO: remove field CremeUser.is_superuser ??
        instance.set_password(self.cleaned_data['password_1'])

        return super(UserAddForm, self).save(*args, **kwargs)


# TODO: factorise with UserAddForm
class UserEditForm(CremeModelForm):
    role = ModelChoiceField(label=_(u"Role"), queryset=UserRole.objects.all(), required=False)

    class Meta:
        model = CremeUser
        fields = ('first_name', 'last_name', 'email', 'role')  # 'is_superuser'

    def __init__(self, *args, **kwargs):
        super(UserEditForm, self).__init__(*args, **kwargs)

        # NB: browser can ignore <em> tag in <option>...
        self.fields['role'].empty_label = u'*%s*' % ugettext(u'Superuser')

    def save(self, *args, **kwargs):
        instance = self.instance
        # NB: needed with django 1.8 when we reset to 'None' (the value seems skipped) => is it a bug ??
        instance.role = role = self.cleaned_data['role']
        instance.is_superuser = (role is None)

        return super(UserEditForm, self).save(*args, **kwargs)


# TODO: see django.contrib.auth.forms.PasswordChangeForm
class UserChangePwForm(CremeForm):
    password_1 = CharField(label=_(u"Password"), min_length=6, widget=PasswordInput())
    password_2 = CharField(label=_(u"Confirm password"), min_length=6, widget=PasswordInput())

    error_messages = {
        'password_mismatch': _(u"Passwords are different"),
    }

    def __init__(self, *args, **kwargs):
        self.user2edit = kwargs.pop('instance')
        super(UserChangePwForm, self).__init__(*args, **kwargs)

    def clean_password_2(self):
        data = self.data
        pw2  = data['password_2']

        if data['password_1'] != pw2:
            raise ValidationError(self.error_messages['password_mismatch'], code='password_mismatch')

        return pw2

    def save(self):
        user = self.user2edit
        user.set_password(self.cleaned_data.get('password_1'))
        user.save()


class TeamCreateForm(CremeModelForm):
    teammates = ModelMultipleChoiceField(queryset=CremeUser.objects.filter(is_team=False, is_staff=False),
                                         # widget=UnorderedMultipleChoiceWidget,
                                         label=_(u"Teammates"), required=False,
                                        )

    class Meta:
        model = CremeUser
        fields = ('username',)

    def __init__(self, *args, **kwargs):
        super(TeamCreateForm, self).__init__(*args, **kwargs)
        self.fields['username'].label = ugettext('Team name')

    def save(self, *args, **kwargs):
        team = self.instance

        team.is_team = True
        super(TeamCreateForm, self).save(*args, **kwargs)

        team.teammates = self.cleaned_data['teammates']

        return team


class TeamEditForm(TeamCreateForm):
    def __init__(self, *args, **kwargs):
        super(TeamEditForm, self).__init__(*args, **kwargs)
        self.fields['teammates'].initial = self.instance.teammates


class UserAssignationForm(CremeForm):
    to_user = ModelChoiceField(label=_(u"Choose a user to transfer to"),
                               queryset=CremeUser.objects.none(),
                              )

    def __init__(self, user, *args, **kwargs):
        super(UserAssignationForm, self).__init__(user, *args, **kwargs)
        self.user_to_delete = user_to_delete= self.initial['user_to_delete']

        users = CremeUser.objects.exclude(pk=user_to_delete.pk).exclude(is_staff=True)
        choices = defaultdict(list)
        for user in users:
            choices[user.is_team].append((user.id, unicode(user)))

        to_user = self.fields['to_user']
        to_user.queryset = users
        to_user.choices =  [(ugettext(u'Users'), choices[False]),
                            (ugettext(u'Teams'), choices[True]),
                           ]

    def save(self, *args, **kwargs):
        mutex = Mutex.get_n_lock('creme_config-forms-user-transfer_user')
        CremeUserForeignKey._TRANSFER_TO_USER = self.cleaned_data['to_user']

        try:
            self.user_to_delete.delete()
        finally:
            CremeUserForeignKey._TRANSFER_TO_USER = None
            mutex.release()
