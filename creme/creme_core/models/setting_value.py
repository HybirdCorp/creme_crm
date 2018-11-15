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

import logging

from django.db import models

from ..core.setting_key import setting_key_registry
from ..global_info import get_per_request_cache


logger = logging.getLogger(__name__)


class SettingValueManager(models.Manager):
    def __init__(self, skey_registry, **kwargs):
        super().__init__(**kwargs)
        self.key_registry = skey_registry

    def get_4_key(self, key, **kwargs):
        """Get the SettingValue corresponding to a SettingKey. Results are cached (per request).

        @param key: A SettingKey instance, or an ID of SettingKey (string).
        @param default: (optional) If given & the SettingValue does not exist,
               a dummy SettingValue which contains this default value is returned.
               BEWARE: you should probably just use the "value" attribute of this dummy object
               (it's not a true SettingValue instance).
        @return: A SettingValue instance.
        @raise: SettingValue.DoesNotExist.
        @raise: KeyError if the SettingKey is not registered.
        """
        # key_id = key if isinstance(key, str) else key.id
        if isinstance(key, str):
            key_id = key
            __key = self.key_registry[key_id]
        else:
            key_id = key.id
            # self.key_registry[key_id] TODO ?

        cache = get_per_request_cache()

        cache_key = 'creme_core-setting_value-{}'.format(key_id)
        sv = cache.get(cache_key)

        if sv is None:
            try:
                sv = cache[cache_key] = self.get(key_id=key_id)
            except self.model.DoesNotExist:
                logger.critical('SettingValue with key_id="%s" cannot be found ! '
                                '(maybe "creme_populate" command has not been run correctly).',
                                key_id
                               )
                if 'default' not in kwargs:
                    raise

                class DummySettingValue:
                    def __init__(self, key_id, value):
                        # self.id = None
                        self.key_id = key_id
                        self.value  = value

                sv = cache[cache_key] = DummySettingValue(key_id=key_id, value=kwargs['default'])

        return sv


class SettingValue(models.Model):
    key_id    = models.CharField(max_length=100)  # See SettingKey.id
    value_str = models.TextField()

    objects = SettingValueManager(skey_registry=setting_key_registry)

    class Meta:
        app_label = 'creme_core'

    def __str__(self):
        return 'SettingValue(key_id="{key}", value_str="{value}")'.format(key=self.key_id, value=self.value_str)

    @property
    def key(self):
        # TODO: pass setting_key_registry as argument ?
        return setting_key_registry[self.key_id]

    @key.setter
    def key(self, skey):
        self.key_id = skey.id

    @property
    def value(self):
        value_str = self.value_str

        # TODO: for string-value, empty an string is returned as <None> => use JSON instead ??
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
