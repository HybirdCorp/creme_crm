# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from itertools import izip

from django.forms import CharField, ChoiceField, BooleanField, MultipleChoiceField, ModelChoiceField
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User

from creme.creme_core.models import UserRole, SetCredentials, Mutex
from creme.creme_core.registry import creme_registry
from creme.creme_core.forms import CremeForm, CremeModelForm, ListEditionField
from creme.creme_core.forms.widgets import UnorderedMultipleChoiceWidget, Label
from creme.creme_core.utils import creme_entity_content_types


_ALL_ENTITIES = list(creme_entity_content_types())

def sorted_entity_models_choices(): #TODO: factorise with other modules ??
    return sorted(((ct.id, unicode(ct)) for ct in _ALL_ENTITIES), key=lambda t: t[1])

def EmptyMultipleChoiceField(required=False, widget=UnorderedMultipleChoiceWidget, *args, **kwargs):
    return MultipleChoiceField(required=required, choices=(), widget=widget, *args, **kwargs)


class UserRoleCreateForm(CremeModelForm):
    creatable_ctypes  = EmptyMultipleChoiceField(label=_(u'Creatable resources'))
    exportable_ctypes = EmptyMultipleChoiceField(label=_(u'Exportable resources'))
    allowed_apps      = EmptyMultipleChoiceField(label=_(u'Allowed applications'))
    admin_4_apps      = EmptyMultipleChoiceField(label=_(u'Administrated applications'))

    class Meta:
        model = UserRole
        exclude = ('raw_allowed_apps', 'raw_admin_4_apps')

    def __init__(self, *args, **kwargs):
        super(UserRoleCreateForm, self).__init__(*args, **kwargs)
        fields = self.fields

        models_choices = sorted_entity_models_choices()
        fields['creatable_ctypes'].choices  = models_choices
        fields['exportable_ctypes'].choices = models_choices

        apps = sorted(((app.name, unicode(app.verbose_name)) for app in creme_registry.iter_apps()), key=lambda t: t[1])
        fields['allowed_apps'].choices = apps
        fields['admin_4_apps'].choices = apps

    def save(self, *args, **kwargs):
        instance = self.instance
        cleaned  = self.cleaned_data

        instance.allowed_apps = cleaned['allowed_apps']
        instance.admin_4_apps = cleaned['admin_4_apps']

        return super(UserRoleCreateForm, self).save(*args, **kwargs)


class UserRoleEditForm(UserRoleCreateForm):
    set_credentials = ListEditionField(content=(), label=_(u'Existing set credentials'),
                                       help_text=_(u'Uncheck the credentials you want to delete.'),
                                       only_delete=True, required=False)

    def __init__(self, *args, **kwargs):
        super(UserRoleEditForm, self).__init__(*args, **kwargs)

        fields = self.fields
        role   = self.instance

        self._creds = role.credentials.all() #get_credentials() ?? problem with cache for updating SetCredentials lines
        self._apps  = role.allowed_apps | role.admin_4_apps

        fields['set_credentials'].content = [unicode(creds) for creds in self._creds]
        fields['allowed_apps'].initial = role.allowed_apps
        fields['admin_4_apps'].initial = role.admin_4_apps

    def save(self, *args, **kwargs):
        role = super(UserRoleEditForm, self).save(*args, **kwargs)

        creds2del = [creds.pk
                        for creds, new_creds in izip(self._creds, self.cleaned_data['set_credentials'])
                            if new_creds is None
                    ]

        if creds2del:
            SetCredentials.objects.filter(pk__in=creds2del).delete()

        return role


class AddCredentialsForm(CremeModelForm):
    can_view   = BooleanField(label=_(u'Can view'),   required=False)
    can_change = BooleanField(label=_(u'Can change'), required=False)
    can_delete = BooleanField(label=_(u'Can delete'), required=False)
    can_link   = BooleanField(label=_(u'Can link'),   required=False, help_text=_(u'You must have the permission to link on 2 entities to create a relationship between them.'))
    can_unlink = BooleanField(label=_(u'Can unlink'), required=False, help_text=_(u'You must have the permission to unlink on 2 entities to delete a relationship between them.'))
    set_type   = ChoiceField(label=_(u'Type of entities set'), choices=SetCredentials.ESETS_MAP.items())
    ctype      = ChoiceField(label=_(u'Apply to a specific type'), choices=()) #TODO: EntityTypeChoiceField ???

    class Meta:
        model = SetCredentials
        exclude = ('role', 'value') #fields ??

    def __init__(self, role, *args, **kwargs):
        super(AddCredentialsForm, self).__init__(*args, **kwargs)
        self.role = role

        choices = [(0, ugettext('None'))]
        choices += sorted_entity_models_choices()
        self.fields['ctype'].choices = choices

    def clean_ctype(self):
        ct_id = int(self.cleaned_data['ctype'])
        return ContentType.objects.get_for_id(ct_id) if ct_id else None

    def save(self, *args, **kwargs):
        instance = self.instance
        get_data = self.cleaned_data.get

        instance.role = self.role
        instance.set_value(get_data('can_view'), get_data('can_change'), get_data('can_delete'),
                           get_data('can_link'), get_data('can_unlink')
                          )

        return super(AddCredentialsForm, self).save(*args, **kwargs)


class UserRoleDeleteForm(CremeForm):
    def __init__(self, user, *args, **kwargs):
        super(UserRoleDeleteForm, self).__init__(user, *args, **kwargs)
        self.role_to_delete = role_2_del = self.initial['role_to_delete']
        self.using_users = users = User.objects.filter(role=role_2_del)

        if users:
            self.fields['to_role'] = ModelChoiceField(label=ugettext('Choose a role to transfer to'),
                                                      queryset=UserRole.objects.exclude(id=role_2_del.id),
                                                     )
        else:
            self.fields['info'] = CharField(label=ugettext('Information'), required=False, widget=Label,
                                            initial=ugettext('This role is not used by any user, you can delete it safely.')
                                           )

    def save(self, *args, **kwargs):
        to_role = self.cleaned_data.get('to_role')
        mutex = Mutex.get_n_lock('creme_config-forms-role-transfer_role')

        try:
            if to_role is not None:
                self.using_users.update(role=to_role)

            self.role_to_delete.delete()
        finally:
            mutex.release()
