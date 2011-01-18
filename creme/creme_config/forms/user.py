# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

import re
from logging import debug

from django.utils.safestring import mark_safe
from django.forms import CharField, ModelChoiceField, ModelMultipleChoiceField, ValidationError
from django.forms.widgets import PasswordInput
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeEntity, Relation, RelationType, UserRole
from creme_core.forms import CremeForm, CremeModelForm
from creme_core.forms.fields import CremeEntityField
from creme_core.forms.widgets import UnorderedMultipleChoiceWidget

from persons.models import Contact, Organisation #TODO: can the 'persons' app hook this form instead of this 'bad' dependence ??


_get_ct = ContentType.objects.get_for_model

#TODO: see django.contrib.auth.forms.UserCreationForm
class UserAddForm(CremeModelForm):
    password_1   = CharField(label=_(u"Password"), min_length=6, widget=PasswordInput(), required=True)
    password_2   = CharField(label=_(u"Confirm password"), min_length=6, widget=PasswordInput(), required=True)
    role         = ModelChoiceField(label=_(u"Role"), queryset=UserRole.objects.all(), required=False,
                                    help_text=_(u"You must choose a role for a non-super user."))
    contact      = CremeEntityField(label=_(u"Related contact"), model=Contact, q_filter={'is_user': None}, required=False,
                                    help_text=_(u"Select the related contact if he already exists (if you don't, a contact will be automatically created)."))
    organisation = ModelChoiceField(label=_(u"User organisation"), queryset=Organisation.get_all_managed_by_creme())
    relation     = ModelChoiceField(label=_(u"Position in the organisation"),
                                    queryset=RelationType.objects.filter(subject_ctypes=_get_ct(Contact), object_ctypes=_get_ct(Organisation)))

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'is_superuser', 'role')

    def clean_username(self):
        username = self.data['username']
        if not re.match("^(\w)[\w-]*$", username):
            raise ValidationError(ugettext(u"The username must only contain alphanumeric (a-z, A-Z, 0-9), "
                                            "hyphen and underscores are allowed (but not as first character)."))
        return username

    def clean_password_2(self):
        cleaned_data = self.cleaned_data
        pw2  = cleaned_data['password_2']

        if cleaned_data['password_1'] != pw2:
            raise ValidationError(ugettext(u"Passwords are different"))

        return pw2

    def clean_role(self):
        cleaned_data = self.cleaned_data

        role = cleaned_data['role']

        if not cleaned_data.get('is_superuser') and not role:
            raise ValidationError(ugettext(u"Choose a role or set superuser status to 'True'."))

        return role

    def save(self, *args, **kwargs):
        cleaned = self.cleaned_data
        user    = self.instance

        user.set_password(cleaned['password_1'])
        super(UserAddForm, self).save(*args, **kwargs)

        contact = cleaned.get('contact', None)

        if not contact:
            contact = Contact(last_name=(user.last_name or user.username),
                              first_name=(user.first_name or user.username),
                              user=user)

        contact.is_user = user
        contact.save()

        Relation.objects.create(subject_entity=contact, type=cleaned['relation'],
                                object_entity=cleaned['organisation'], user=user,
                               )

        user.update_credentials()

        return user


#TODO: factorise with UserAddForm
class UserEditForm(CremeModelForm):
    role = ModelChoiceField(label=_(u"Role"), queryset=UserRole.objects.all(), required=False,
                            help_text=_(u"You must choose a role for a non-super user."))

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'is_superuser', 'role')

    def __init__(self, *args, **kwargs):
        super(UserEditForm, self).__init__(*args, **kwargs)
        self.old_role_id = self.instance.role_id

    def clean_role(self):
        cleaned_data = self.cleaned_data

        role = cleaned_data['role']

        if not cleaned_data.get('is_superuser') and not role:
            raise ValidationError(ugettext(u"Choose a role or set superuser status to 'True'."))

        return role

    def save(self, *args, **kwargs):
        user = super(UserEditForm, self).save(*args, **kwargs)

        if user.role_id != self.old_role_id:
            debug('Role has changed for user="%s" => update credentials', user)
            user.update_credentials()

        return user

#TODO: see django.contrib.auth.forms.PasswordChangeForm
class UserChangePwForm(CremeForm):
    password_1 = CharField(label=_(u"Password"), min_length=6, widget=PasswordInput())
    password_2 = CharField(label=_(u"Confirm password"), min_length=6, widget=PasswordInput())

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('instance')
        super(UserChangePwForm, self).__init__(*args, **kwargs)

    def clean_password_2(self):
        data = self.data
        pw2  = data['password_2']

        if data['password_1'] != pw2:
            raise ValidationError(ugettext(u"Passwords are different"))

        return pw2

    def save(self):
        user = self.user
        user.set_password(self.cleaned_data.get('password_1'))
        user.save()


class TeamCreateForm(CremeModelForm):
    teammates = ModelMultipleChoiceField(queryset=User.objects.filter(is_team=False),
                                         widget=UnorderedMultipleChoiceWidget,
                                         label=_(u"Teammates"), required=False)

    class Meta:
        model = User
        fields = ('username',)

    def __init__(self, *args, **kwargs):
        super(TeamCreateForm, self).__init__(*args, **kwargs)
        self.fields['username'].label = ugettext('Team name')

    def save(self, *args, **kwargs):
        team = self.instance

        team.is_team = True
        super(TeamCreateForm, self).save(*args, **kwargs)

        team.teammates = self.cleaned_data['teammates']


class TeamEditForm(TeamCreateForm):
    def __init__(self, *args, **kwargs):
        super(TeamEditForm, self).__init__(*args, **kwargs)
        self.fields['teammates'].initial = self.instance.teammates.iterkeys()
