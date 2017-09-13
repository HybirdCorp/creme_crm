# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2017  Hybird
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

import warnings

from django.conf import settings
from django.db.models import Model, CharField, TextField, ForeignKey

from ..core.setting_key import setting_key_registry


class SettingValue(Model):
    key_id    = CharField(max_length=100)  # See SettingKey.id
    user      = ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True)
    value_str = TextField()

    class Meta:
        app_label = 'creme_core'

    def __init__(self, *args, **kwargs):
        super(SettingValue, self).__init__(*args, **kwargs)
        if self.user_id:
            warnings.warn("SettingValue.user attribute is deprecated ; use UserSettingValue instead.",
                          DeprecationWarning
                         )

    @property
    def key(self):
        return setting_key_registry[self.key_id]

    @key.setter
    def key(self, skey):
        self.key_id = skey.id

    @property
    def value(self):
        # return self.key.cast(self.value_str)
        value_str = self.value_str

        return self.key.cast(value_str) if value_str else None

    @value.setter
    def value(self, value):
        # self.value_str = str(value)

        if value is None:
            if not self.key.blank:
                raise ValueError('SettingValue.value: a value is required (key is not <blank=True>.')

            self.value_str = ''
        else:
            value_str = str(value)
            self.key.cast(value_str)  # raises ValueError
            self.value_str = value_str

    @property
    def as_html(self):
        # return self.key.value_as_html(self.value)
        value = self.value

        return self.key.value_as_html(value) if value is not None else ''

    @staticmethod
    def create_if_needed(key, user, value):
        warnings.warn("SettingValue.create_if_needed() is deprecated ; "
                      "use SettingValue.objects.get_or_create() instead.",
                      DeprecationWarning
                     )

        return SettingValue.objects.get_or_create(key_id=key.id, user=user,
                                                  defaults={'value': value},
                                                 )[0]
