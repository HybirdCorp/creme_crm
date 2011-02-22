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

from itertools import izip
from logging import debug

from django.forms import ChoiceField, BooleanField, ModelMultipleChoiceField, MultipleChoiceField
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User

from creme_core.models import UserRole, SetCredentials, EntityCredentials
from creme_core.registry import creme_registry
from creme_core.forms import CremeForm, CremeModelForm
from creme_core.forms.fields import ListEditionField
from creme_core.forms.widgets import UnorderedMultipleChoiceWidget
from creme_core.utils import Q_creme_entity_content_types


_ALL_APPS = [(app.name, app.verbose_name) for app in creme_registry.iter_apps()]

class UserRoleCreateForm(CremeModelForm):
    creatable_ctypes = ModelMultipleChoiceField(label=_(u'Creatable resources'),
                                                queryset=Q_creme_entity_content_types(),
                                                required=False,
                                                widget=UnorderedMultipleChoiceWidget)
    allowed_apps     = MultipleChoiceField(label=_(u'Allowed applications'),
                                           choices=_ALL_APPS, required=False,
                                           widget=UnorderedMultipleChoiceWidget)
    admin_4_apps     = MultipleChoiceField(label=_(u'Administrated applications'),
                                           choices=_ALL_APPS, required=False,
                                           widget=UnorderedMultipleChoiceWidget)

    class Meta:
        model = UserRole
        exclude = ('raw_allowed_apps', 'raw_admin_4_apps')

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

        creds2del = [creds.pk for creds, new_creds in izip(self._creds, self.cleaned_data['set_credentials'])
                            if new_creds is None]

        if creds2del:
            SetCredentials.objects.filter(pk__in=creds2del).delete()

        if creds2del or (self._apps != role.allowed_apps | role.admin_4_apps):
            debug('Role "%s" has changed => update credentials', role)

            for user in User.objects.filter(role=role):
                user.role = role
                user.update_credentials()

        return role


class AddCredentialsForm(CremeModelForm):
    can_view   = BooleanField(label=_(u'Can view'),   required=False)
    can_change = BooleanField(label=_(u'Can change'), required=False)
    can_delete = BooleanField(label=_(u'Can delete'), required=False)
    can_link   = BooleanField(label=_(u'Can link'),   required=False, help_text=_(u'You must have the permission to link on 2 entities to create a relationship between them.'))
    can_unlink = BooleanField(label=_(u'Can unlink'), required=False, help_text=_(u'You must have the permission to unlink on 2 entities to delete a relationship between them.'))
    set_type   = ChoiceField(label=_(u'Type of entities set'), choices=SetCredentials.ESET_MAP.items())

    class Meta:
        model = SetCredentials
        exclude = ('role', 'value') #fields ??

    def __init__(self, role, *args, **kwargs):
        super(AddCredentialsForm, self).__init__(*args, **kwargs)
        self.role = role

    def save(self, *args, **kwargs):
        instance = self.instance
        get_data = self.cleaned_data.get
        role     = self.role

        instance.role = role
        instance.set_value(get_data('can_view'), get_data('can_change'), get_data('can_delete'),
                           get_data('can_link'), get_data('can_unlink')
                          )

        super(AddCredentialsForm, self).save(*args, **kwargs)

        for user in User.objects.filter(role=role):
            debug('Role "%s" has changed => update credentials for user: %s', role, user)
            user.update_credentials()

        return instance


class DefaultCredsForm(CremeForm):
    can_view   = BooleanField(label=_(u'Can view'),   required=False)
    can_change = BooleanField(label=_(u'Can change'), required=False)
    can_delete = BooleanField(label=_(u'Can delete'), required=False)
    can_link   = BooleanField(label=_(u'Can link'),   required=False)
    can_unlink = BooleanField(label=_(u'Can unlink'), required=False)

    def __init__(self, *args, **kwargs):
        super(DefaultCredsForm, self).__init__(*args, **kwargs)

        fields   = self.fields
        defcreds = EntityCredentials.get_default_creds()

        fields['can_view'].initial   = defcreds.can_view()
        fields['can_change'].initial = defcreds.can_change()
        fields['can_delete'].initial = defcreds.can_delete()
        fields['can_link'].initial   = defcreds.can_link()
        fields['can_unlink'].initial = defcreds.can_unlink()

    def save(self):
        get_data = self.cleaned_data.get
        EntityCredentials.set_default_perms(view=get_data('can_view'),
                                            change=get_data('can_change'),
                                            delete=get_data('can_delete'),
                                            link=get_data('can_link'),
                                            unlink=get_data('can_unlink'),
                                           )
