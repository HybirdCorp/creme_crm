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

import logging
from json import loads as json_load
from typing import Any, Callable, Dict, Iterator, Type

from django.db.models import Model, TextField
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from ..utils import bool_as_html, bool_from_str
from ..utils.serializers import json_encode

logger = logging.getLogger(__name__)


# TODO: move to utils ? rename hour_to_str() ?
def print_hour(value) -> str:
    return _('{hour}h').format(hour=value)


class _SettingKey:
    STRING = 1
    INT    = 2
    BOOL   = 3
    HOUR   = 10
    EMAIL  = 20

    _CASTORS: Dict[int, Callable[[str], Any]] = {
        STRING: str,
        INT:    int,
        BOOL:   bool_from_str,
        HOUR:   int,  # TODO: validate 0 =< x =< 23  ??
        EMAIL:  str,
    }

    HTML_PRINTERS: Dict[int, Callable[[Any], str]] = {
        BOOL:   bool_as_html,
        HOUR:   print_hour,
    }

    id: str
    app_label: str
    type: int
    hidden: bool

    def __init__(self,
                 id: str,
                 description: str,
                 app_label: str,
                 type: int = STRING,
                 hidden: bool = False,
                 blank: bool = False):
        """Constructor.
        @param id: Unique String. Use something like 'my_app-key_name'
        @param description: Used in the configuration GUI ;
               use a gettext_lazy() instance ('' is OK if hidden==True).
        @param app_label: Eg: 'creme_core'
        @param type: Integer ; see: _SettingKey.STRING, _SettingKey.INT ...
        @param hidden: Boolean. If True, it can not be seen in the configuration GUI.
        @param blank: Boolean. If True, the value is not required in the configuration GUI.
        """
        self.id          = id
        self.description = description
        self.app_label   = app_label
        self.type        = type
        self.hidden      = hidden
        self.blank       = blank

        self._castor = self._CASTORS[type]

    def __str__(self):
        return (
            f'{self.__class__.__name__}('
            f'id="{self.id}", '
            f'description="{self.description}", '
            f'app_label="{self.app_label}", '
            f'type={self.type}, '
            f'hidden={self.hidden}, '
            f'blank={self.blank}'
            f')'
        )

    def cast(self, value_str: str):
        return self._castor(value_str)

    @property
    def description_html(self):
        return mark_safe('<br/>'.join(
            escape(d) for d in self.description.split('\n')
        ))

    def value_as_html(self, value) -> str:
        printer = self.HTML_PRINTERS.get(self.type)
        if printer is not None:
            value = printer(value)

        return value


class SettingKey(_SettingKey):
    pass


class UserSettingKey(_SettingKey):
    _CASTORS = {
        _SettingKey.STRING: str,
        _SettingKey.INT:    int,
        _SettingKey.BOOL:   bool,  # TODO: fix _SettingKey to use JSON ('True' => 'true') ??
        _SettingKey.HOUR:   int,
        _SettingKey.EMAIL:  str,
    }


# TODO: would be cool to declare class _SettingKeyRegistry[Type[_SettingKey]] ...
class _SettingKeyRegistry:
    class RegistrationError(Exception):
        pass

    def __init__(self, key_class: Type[_SettingKey] = SettingKey):
        self._skeys: Dict[str, _SettingKey] = {}
        self._key_class: Type[_SettingKey] = key_class

    def __getitem__(self, key_id: str) -> _SettingKey:
        return self._skeys[key_id]

    def __iter__(self) -> Iterator[_SettingKey]:
        return iter(self._skeys.values())

    def register(self, *skeys: _SettingKey) -> None:
        setdefault = self._skeys.setdefault
        key_class = self._key_class

        for skey in skeys:
            if not isinstance(skey, key_class):
                raise self.RegistrationError(
                    f"Bad class for key {skey} (need {key_class})"
                )

            if setdefault(skey.id, skey) is not skey:
                raise self.RegistrationError(
                    f"Duplicated setting key's id: {skey.id}"
                )

    def unregister(self, *skeys: _SettingKey) -> None:
        pop = self._skeys.pop

        for skey in skeys:
            if pop(skey.id, None) is None:
                raise self.RegistrationError(
                    f'This Setting is not registered (already un-registered ?): {skey.id}'
                )


setting_key_registry = _SettingKeyRegistry(SettingKey)
user_setting_key_registry = _SettingKeyRegistry(UserSettingKey)


class UserSettingValueManager:
    """Manager related to a user which can read & write setting values stored
    in a TextField (serialized to JSON).
    See the property <creme_core.models.CremeUser.settings>.
    """
    class ReadOnlyError(Exception):
        pass

    def __init__(self, user_class: Type[Model], user_id, json_settings: TextField):
        self._user_class = user_class
        self._user_id = user_id
        self._values = json_load(json_settings)
        self._read_only = True

    def __enter__(self):
        self._read_only = False

        return self

    def __exit__(self, exc_type, exc_value, tb):
        self._read_only = True

        if exc_value:
            # TODO: do we need a non-atomic mode which saves anyway ?
            logger.warning(
                'UserSettingValueManager: an exception has been raised, '
                'changes will not be saved !'
            )
            raise exc_value

        # TODO: do not hard code the name of the field "json_settings"
        self._user_class.objects.filter(
            pk=self._user_id,
        ).update(json_settings=json_encode(self._values))

        return True

    def __getitem__(self, key: UserSettingKey):
        "@raise KeyError."
        return key.cast(self._values[key.id])

    # TODO: accept key or key_id ??
    def __setitem__(self, key: UserSettingKey, value):
        if self._read_only:
            raise self.ReadOnlyError

        casted_value = key.cast(value)
        self._values[key.id] = casted_value

        return casted_value

    def __delitem__(self, key: UserSettingKey):
        self.pop(key)

    def as_html(self, key: UserSettingKey) -> str:
        return key.value_as_html(self[key])

    def get(self, key: UserSettingKey, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def pop(self, key: UserSettingKey, *default):
        if self._read_only:
            raise self.ReadOnlyError

        return self._values.pop(key.id, *default)

    # TODO:  __contains__ ??
