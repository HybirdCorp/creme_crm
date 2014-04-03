# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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
from collections import defaultdict

from django.forms import CharField, ModelChoiceField, ModelMultipleChoiceField
from django.forms.util import ValidationError, ErrorList
from django.forms.widgets import PasswordInput
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.auth.models import User
#from django.contrib.contenttypes.models import ContentType

from creme.creme_core.models import UserRole, Mutex #Relation, RelationType
from creme.creme_core.models.fields import CremeUserForeignKey
from creme.creme_core.forms import CremeForm, CremeModelForm
#from creme.creme_core.forms.fields import CreatorEntityField
from creme.creme_core.forms.widgets import UnorderedMultipleChoiceWidget

from creme.persons.models import Contact # Organisation #TODO: can the 'persons' app hook this form instead of this 'bad' dependence ??


#_get_ct = ContentType.objects.get_for_model

#TODO: see django.contrib.auth.forms.UserCreationForm
class UserAddForm(CremeModelForm):
    password_1   = CharField(label=_('Password'), min_length=6, widget=PasswordInput())
    password_2   = CharField(label=_('Confirm password'), min_length=6, widget=PasswordInput())
    role         = ModelChoiceField(label=_('Role'), required=False,
                                    queryset=UserRole.objects.all(),
                                    help_text=_('You must choose a role for a non-super user.'),
                                   )
    #contact      = CreatorEntityField(label=_(u"Related contact"), model=Contact, q_filter={'is_user': None}, required=False,
                                      #help_text=_(u"Select the related contact if he already exists (if you don't, a contact will be automatically created)."))
    #organisation = ModelChoiceField(label=_(u"User organisation"), queryset=Organisation.get_all_managed_by_creme(), empty_label=None)
    #relation     = ModelChoiceField(label=_(u"Position in the organisation"), empty_label=None,
                                    #queryset=RelationType.objects.filter(subject_ctypes=_get_ct(Contact), object_ctypes=_get_ct(Organisation))
                                   #)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'is_superuser', 'role')

    def clean_username(self):
        username = self.cleaned_data['username']

        if not re.match("^(\w)[\w-]*$", username):
            raise ValidationError(ugettext(u"The username must only contain alphanumeric (a-z, A-Z, 0-9), "
                                            "hyphen and underscores are allowed (but not as first character)."
                                           )
                                 )

        return username

    #def clean_password_2(self):
        #cleaned_data = self.cleaned_data
        #pw2  = cleaned_data['password_2']

        #if cleaned_data['password_1'] != pw2:
            #raise ValidationError(ugettext(u"Passwords are different"))

        #return pw2

    def clean_role(self):
        cleaned_data = self.cleaned_data

        role = cleaned_data['role']

        if not cleaned_data.get('is_superuser') and not role:
            raise ValidationError(ugettext(u"Choose a role or set superuser status to 'True'."))

        return role

    def clean(self):
        cleaned = self.cleaned_data

        if not self._errors and cleaned['password_1'] != cleaned['password_2']:
            self.errors['password_2'] = ErrorList([ugettext(u'Passwords are different')])

        return cleaned

    def save(self, *args, **kwargs):
        cleaned = self.cleaned_data
        user    = self.instance

        user.set_password(cleaned['password_1'])
        super(UserAddForm, self).save(*args, **kwargs)

        #contact = cleaned.get('contact', None)

        #if not contact:
            #contact = Contact(last_name=(user.last_name or user.username),
                              #first_name=(user.first_name or user.username),
                              #user=user
                             #)

        #contact.is_user = user
        #contact.save()

        #relation_desc = {'subject_entity': contact,
                         #'type':           cleaned['relation'],
                         #'object_entity':  cleaned['organisation'],
                        #}
        #if not Relation.objects.filter(**relation_desc).exists():
            #Relation.objects.create(user=user, **relation_desc)

        return user


#TODO: factorise with UserAddForm
class UserEditForm(CremeModelForm):
    role = ModelChoiceField(label=_(u"Role"), queryset=UserRole.objects.all(), required=False,
                            help_text=_(u"You must choose a role for a non-super user."),
                           )

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'is_superuser', 'role')

    def clean_role(self):
        cleaned_data = self.cleaned_data

        role = cleaned_data['role']

        if not cleaned_data.get('is_superuser') and not role:
            raise ValidationError(ugettext(u"Choose a role or set superuser status to 'True'."))

        return role


#TODO: see django.contrib.auth.forms.PasswordChangeForm
class UserChangePwForm(CremeForm):
    password_1 = CharField(label=_(u"Password"), min_length=6, widget=PasswordInput())
    password_2 = CharField(label=_(u"Confirm password"), min_length=6, widget=PasswordInput())

    def __init__(self, *args, **kwargs):
        self.user2edit = kwargs.pop('instance')
        super(UserChangePwForm, self).__init__(*args, **kwargs)

    def clean_password_2(self):
        data = self.data
        pw2  = data['password_2']

        if data['password_1'] != pw2:
            raise ValidationError(ugettext(u"Passwords are different"))

        return pw2

    def save(self):
        user = self.user2edit
        user.set_password(self.cleaned_data.get('password_1'))
        user.save()


class TeamCreateForm(CremeModelForm):
    teammates = ModelMultipleChoiceField(queryset=User.objects.filter(is_team=False, is_staff=False),
                                         widget=UnorderedMultipleChoiceWidget,
                                         label=_(u"Teammates"), required=False,
                                        )

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

        return team


class TeamEditForm(TeamCreateForm):
    def __init__(self, *args, **kwargs):
        super(TeamEditForm, self).__init__(*args, **kwargs)
        self.fields['teammates'].initial = self.instance.teammates


class UserAssignationForm(CremeForm):
    to_user = ModelChoiceField(label=_(u"Choose a user to transfer to"),
                               queryset=User.objects.none()
                              )

    def __init__(self, user, *args, **kwargs):
        super(UserAssignationForm, self).__init__(user, *args, **kwargs)
        self.user_to_delete = user_to_delete= self.initial['user_to_delete']

        users = User.objects.exclude(pk=user_to_delete.pk).exclude(is_staff=True)
        choices = defaultdict(list)
        for user in users:
            choices[user.is_team].append((user.id, unicode(user)))

        to_user = self.fields['to_user']
        to_user.queryset = users
        to_user.choices =  [(ugettext(u'Users'), choices[False]),
                            (ugettext(u'Teams'), choices[True]),
                           ]

    def save(self, *args, **kwargs):
        user_2_delete = self.user_to_delete

        Contact.objects.filter(is_user=user_2_delete).update(is_user=None)#TODO: Don't know why SET_NULL doesn't work on Contact.is_user

        mutex = Mutex.get_n_lock('creme_config-forms-user-transfer_user')
        CremeUserForeignKey._TRANSFER_TO_USER = self.cleaned_data['to_user']
        try:
            user_2_delete.delete()
        finally:
            CremeUserForeignKey._TRANSFER_TO_USER = None
            mutex.release()
