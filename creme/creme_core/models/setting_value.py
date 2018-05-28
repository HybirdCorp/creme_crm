# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from django.db import models

from ..core.setting_key import setting_key_registry


class SettingValue(models.Model):
    key_id    = models.CharField(max_length=100)  # See SettingKey.id
    value_str = models.TextField()

    class Meta:
        app_label = 'creme_core'

    @property
    def key(self):
        return setting_key_registry[self.key_id]

    @key.setter
    def key(self, skey):
        self.key_id = skey.id

    @property
    def value(self):
        value_str = self.value_str

        return self.key.cast(value_str) if value_str else None

    @value.setter
    def value(self, value):
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
        value = self.value

        return self.key.value_as_html(value) if value is not None else ''
