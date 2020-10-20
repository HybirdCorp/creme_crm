# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

from typing import Union

from django.db import transaction

from creme.creme_core.core.setting_key import SettingKey
from creme.creme_core.models.setting_value import SettingValue


def get_setting_value(key: Union[SettingKey, str], default=None):
    if not key:
        raise KeyError('Empty setting key')

    try:
        return SettingValue.objects.get_4_key(key, default=default).value
    except KeyError:
        return default


def has_setting_value(key: Union[SettingKey, str]):
    if not key:
        raise KeyError('Empty setting key')

    key_id = key if isinstance(key, str) else key.id
    return SettingValue.objects.filter(key_id=key_id).exists()


def set_setting_value(key: Union[SettingKey, str], value):
    if not key:
        raise KeyError('Empty setting key')

    key_id = key if isinstance(key, str) else key.id

    with transaction.atomic():
        if value is None:
            SettingValue.objects.filter(key_id=key_id).delete()
        else:
            setting, created = SettingValue.objects.get_or_create(
                key_id=key_id,
                defaults={'value': value}
            )

            if not created:
                setting.value = value
                setting.save()

        SettingValue.objects.clear_cache_of(key_id)
