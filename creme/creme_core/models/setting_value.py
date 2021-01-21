# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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
from typing import Dict, Union

from django.db import models, transaction

from ..core.setting_key import (
    SettingKey,
    _SettingKeyRegistry,
    setting_key_registry,
)
from ..global_info import get_per_request_cache

logger = logging.getLogger(__name__)


class SettingValueManager(models.Manager):
    class DummySettingValue:
        def __init__(self, key_id, value):
            self.key_id = key_id
            self.value = value

    cache_key_fmt = 'creme_core-setting_value-{}'

    key_registry: _SettingKeyRegistry

    def __init__(self, skey_registry: _SettingKeyRegistry, **kwargs):
        super().__init__(**kwargs)
        self.key_registry = skey_registry

    def exists_4_key(self, key: Union[SettingKey, str]):
        """Check if a SettingValue exists

        @param key: A SettingKey instance, or an ID of SettingKey (string).
        """
        key_id = key if isinstance(key, str) else key.id
        return self.filter(key_id=key_id).exists()

    def set_4_key(self, key: Union[SettingKey, str], value):
        """Set the SettingValue corresponding to a SettingKey. The cache will be cleared.

        @param key: A SettingKey instance, or an ID of SettingKey (string).
        """
        key_id = key if isinstance(key, str) else key.id

        with transaction.atomic():
            if value is None:
                self.filter(key_id=key_id).delete()
            else:
                setting, created = self.get_or_create(
                    key_id=key_id,
                    defaults={'value': value}
                )

                if not created:
                    setting.value = value
                    setting.save()

        # Clear setting key cache
        cache = get_per_request_cache()
        cache_key = self.cache_key_fmt.format(key_id)
        cache.pop(cache_key, None)

    def value_4_key(self, key: Union[SettingKey, str], default=None):
        """Get the SettingValue value or default if not filled.

        @param key: A SettingKey instance, or an ID of SettingKey (string).
        @param default: (optional) If given & the SettingValue does not exist,
        """
        try:
            return self.get_4_key(key, default=default).value
        except KeyError:
            return default

    def get_4_key(self, key: Union[SettingKey, str], **kwargs) -> 'SettingValue':
        """Get the SettingValue corresponding to a SettingKey. Results are cached (per request).

        @param key: A SettingKey instance, or an ID of SettingKey (string).
        @param default: (optional) If given & the SettingValue does not exist,
               a dummy SettingValue which contains this default value is returned.
               BEWARE: you should probably just use the "value" attribute of this dummy object
               (it's not a true SettingValue instance -- see 'DummySettingValue').
        @return: A SettingValue instance.
        @raise: SettingValue.DoesNotExist.
        @raise: KeyError if the SettingKey is not registered.
        """
        return next(iter(self.get_4_keys({'key': key, **kwargs}).values()))

    def get_4_keys(self, *values_info: dict) -> Dict[str, 'SettingValue']:
        """Get several SettingValue corresponding to several SettingKeys at once.
         It's faster than calling 'get_4_key()' several times, because only one
         SQL query is performed (in the worst case)
         Results are cached (per request).

        @param values_info: Each argument must be dictionary with these keys:
               "key": A SettingKey instance, or an ID of SettingKey (string).
               "default": (optional) If given & the SettingValue does not exist,
               a dummy SettingValue which contains this default value is returned.
               BEWARE: you should probably just use the "value" attribute of this dummy object
               (it's not a true SettingValue instance).
        @return: A dictionary.
                 Keys are SettingValue IDs ; values are SettingValues instances.
        @raise: SettingValue.DoesNotExist if one value does not exist & no
                default value has been given.
        @raise: KeyError if the SettingKey is not registered.

        > sk1 = SettingKey(id='....')
        > sk2 = SettingKey(id='....')
        > ....
        > svalues = SettingValue.objects.get_4_keys({'key': sk1.id}, {'key': sk2})
        {sk1.id: SettingValue(...), sk2.id: SettingValue(...)}
        """
        svalues = {}
        cache = get_per_request_cache()
        uncached_info = []
        format_cache_key = self.cache_key_fmt.format

        for value_info in values_info:
            key = value_info['key']

            if isinstance(key, str):
                key_id = key
                self.key_registry[key_id]  # NOQA
            else:
                key_id = key.id
                # self.key_registry[key_id] TODO ?

            cache_key = format_cache_key(key_id)
            sv = cache.get(cache_key)

            if sv is None:
                uncached_info.append((key_id, cache_key, value_info))
            else:
                svalues[key_id] = sv

        if uncached_info:
            retrieved_svalues = {
                svalue.key_id: svalue
                for svalue in self.filter(key_id__in=[i[0] for i in uncached_info])
            }

            for key_id, cache_key, value_info in uncached_info:
                try:
                    sv = retrieved_svalues[key_id]
                except KeyError as e:
                    logger.critical(
                        'SettingValue with key_id="%s" cannot be found ! '
                        '(maybe "creme_populate" command has not been run correctly).',
                        key_id
                    )

                    if 'default' not in value_info:
                        raise self.model.DoesNotExist(
                            f'The instance of {self.model} with key_id="{key_id}" does not exist'
                        ) from e

                    sv = self.DummySettingValue(key_id=key_id, value=value_info['default'])

                svalues[key_id] = cache[cache_key] = sv

        return svalues


class SettingValue(models.Model):
    key_id    = models.CharField(max_length=100)  # See SettingKey.id
    value_str = models.TextField()

    objects = SettingValueManager(skey_registry=setting_key_registry)

    class Meta:
        app_label = 'creme_core'

    def __str__(self):
        return f'SettingValue(key_id="{self.key_id}", value_str="{self.value_str}")'

    @property
    def key(self) -> SettingKey:
        # return setting_key_registry[self.key_id]
        return type(self).objects.key_registry[self.key_id]

    @key.setter
    def key(self, skey: SettingKey):
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
                raise ValueError(
                    'SettingValue.value: a value is required (key is not <blank=True>.'
                )

            self.value_str = ''
        else:
            value_str = str(value)
            self.key.cast(value_str)  # raises ValueError
            self.value_str = value_str

    @property
    def as_html(self) -> str:
        value = self.value

        return self.key.value_as_html(value) if value is not None else ''
