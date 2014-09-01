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

from django.contrib.auth.models import User
from django.db.models import Model, CharField, TextField, ForeignKey
from django.utils.translation import ugettext as _

from ..core.setting_key import SettingKey, setting_key_registry
from ..utils import bool_as_html


#TODO: move to utils
def print_hour(value):
    return _('%sh') % value


#TODO: Add a null and blank attribute ?? And a unique together with key, user
class SettingValue(Model):
    key_id    = CharField(max_length=100) #see SettingKey.id
    user      = ForeignKey(User, blank=True, null=True)
    value_str = TextField()

    class Meta:
        app_label = 'creme_core'

    _HTML_PRINTERS = {
            SettingKey.BOOL:   bool_as_html,
            SettingKey.HOUR:   print_hour,
        }

    @property
    def key(self):
        return setting_key_registry[self.key_id]

    @key.setter
    def key(self, skey):
        self.key_id = skey.id

    @property
    def value(self):
        return self.key.cast(self.value_str)

    @value.setter
    def value(self, value):
        self.value_str = str(value)

    @property
    def as_html(self):
        value = self.value

        printer = self._HTML_PRINTERS.get(self.key.type)
        if printer is not None:
            value = printer(value)

        return value

    @staticmethod
    def create_if_needed(key, user, value):
        return SettingValue.objects.get_or_create(key_id=key.id, user=user,
                                                  defaults={'value': value},
                                                 )[0]
