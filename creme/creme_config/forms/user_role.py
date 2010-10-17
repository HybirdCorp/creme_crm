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

from django.forms import ChoiceField, BooleanField
from django.utils.translation import ugettext_lazy as _

from creme_core.models import UserRole, SetCredentials
from creme_core.forms import CremeModelForm
from creme_core.forms.fields import ListEditionField


class UserRoleCreateForm(CremeModelForm):
    class Meta:
        model = UserRole


class UserRoleEditForm(CremeModelForm):
    set_credentials = ListEditionField(content=(), label=_(u'Existing set credentials'),
                                       help_text=_(u'Uncheck the credentials you want to delete.'),
                                       only_delete=True)

    class Meta:
        model = UserRole

    def __init__(self, *args, **kwargs):
        super(UserRoleEditForm, self).__init__(*args, **kwargs)

        self._creds = self.instance.credentials.all() #get_credentials() ?? problem with cache for updating SetCredentials lines
        self.fields['set_credentials'].content = [unicode(creds) for creds in self._creds]

    def save(self, *args, **kwargs):
        role = super(UserRoleEditForm, self).save(*args, **kwargs)

        creds2del = [creds.pk for creds, new_creds in izip(self._creds, self.cleaned_data['set_credentials'])
                            if new_creds is None]

        if creds2del:
            SetCredentials.objects.filter(pk__in=creds2del).delete()
            #TODO: user.update_credentials() !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        return role


class AddCredentialsForm(CremeModelForm):
    can_view   = BooleanField(label=_(u'Can view'), required=False)
    can_change = BooleanField(label=_(u'Can change'), required=False)
    can_delete = BooleanField(label=_(u'Can delete'), required=False)
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

        instance.role = self.role
        instance.set_value(get_data('can_view'), get_data('can_change'), get_data('can_delete'))

        #TODO: user.update_credentials() !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        return super(AddCredentialsForm, self).save(*args, **kwargs)
