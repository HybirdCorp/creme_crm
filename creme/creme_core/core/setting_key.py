################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from __future__ import annotations

import logging
# import warnings
from collections.abc import Callable, Iterator
from functools import partial
from json import loads as json_load
from typing import Any

from django import forms
from django.db.models import Model, TextField
from django.utils.formats import number_format
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from ..utils import bool_as_html
from ..utils.serializers import json_encode

logger = logging.getLogger(__name__)


# TODO: move to utils ? rename hour_to_str() ?
def print_hour(value) -> str:
    return _('{hour}h').format(hour=value)


class _NeverRequiredBooleanField(forms.BooleanField):
    def __init__(self, **kwargs):
        kwargs['required'] = False
        super().__init__(**kwargs)


class _SettingKey:
    STRING = 1
    INT    = 2
    BOOL   = 3
    HOUR   = 10
    EMAIL  = 20

    _CASTORS: dict[int, Callable[[str], Any]] = {
        STRING: str,
        INT:    int,
        BOOL:   bool,
        HOUR:   int,  # TODO: validate 0 =< x =< 23  ??
        EMAIL:  str,  # TODO: validate email?
    }

    HTML_PRINTERS: dict[int, Callable[[Any], str]] = {
        INT:    partial(number_format, force_grouping=True),
        BOOL:   bool_as_html,
        HOUR:   print_hour,
    }

    FORM_FIELDS = {
        STRING: partial(forms.CharField, widget=forms.Textarea),
        INT:    forms.IntegerField,
        BOOL:   _NeverRequiredBooleanField,
        # TODO: an HourField inheriting ChoiceField ?? (+factorise with 'polls')
        HOUR:   partial(forms.IntegerField, min_value=0, max_value=23),
        EMAIL:  forms.EmailField,
    }

    def __init__(self, *,
                 id: str,
                 description: str,
                 app_label: str,
                 type: int = STRING,
                 hidden: bool = False,
                 blank: bool = False,
                 formfield_class: type[forms.Field] | None = None,
                 html_printer: Callable[[Any], str] | None = None,
                 ):
        """Constructor.
        @param id: Unique String. Use something like "my_app-key_name".
        @param description: Used in the configuration GUI ;
               use a gettext_lazy() instance ('' is OK if hidden==True).
        @param app_label: E.g. "creme_core".
        @param see: _SettingKey.STRING, _SettingKey.INT ...
        @param hidden: If True, it can not be seen in the configuration GUI.
        @param blank: If True, the value is not required in the configuration GUI.
        @param formfield_class: Field to use in the form to set the related value.
        @param html_printer: Function to render the related value as HTML;
               it must take one argument (the string value).
        """
        self.id: str = id
        self.description: str = description
        self.app_label: str = app_label
        self.type: int = type
        self.hidden: bool = hidden
        self.blank: bool = blank
        self.formfield_class = formfield_class
        self.html_printer = html_printer

        self._castor = self._CASTORS[type]

    def __str__(self):
        return (
            f'{self.__class__.__name__}('
            f'id="{self.id}", '
            f'description="{self.description}", '
            f'app_label="{self.app_label}", '
            f'type={self.type}, '
            f'hidden={self.hidden}, '
            f'blank={self.blank}, '
            f'formfield_class={self.formfield_class}'
            f')'
        )

    # TODO: rework? (now we take casted value from formfield & deserialized JSON)
    def cast(self, value: Any):
        return self._castor(value)

    @property
    def description_html(self):
        return mark_safe('<br/>'.join(
            escape(d) for d in self.description.split('\n')
        ))

    def formfield(self):
        form_cls = self.formfield_class or self.FORM_FIELDS.get(self.type, forms.CharField)

        return form_cls(label=_('Value'), required=not self.blank)

    def value_as_html(self, value: Any) -> str:
        """@param: value: Value casted in the final type (integer, bool)"""
        printer = self.html_printer or self.HTML_PRINTERS.get(self.type, str)

        return printer(value)


class SettingKey(_SettingKey):
    pass


class UserSettingKey(_SettingKey):
    pass


# TODO: would be cool to declare class _SettingKeyRegistry[Type[_SettingKey]] ...
class SettingKeyRegistry:
    class RegistrationError(Exception):
        pass

    def __init__(self, key_class: type[_SettingKey] = SettingKey):
        self._skeys: dict[str, _SettingKey] = {}
        self._key_class: type[_SettingKey] = key_class

    def __getitem__(self, key_id: str) -> _SettingKey:
        return self._skeys[key_id]

    def __iter__(self) -> Iterator[_SettingKey]:
        return iter(self._skeys.values())

    def register(self, *skeys: _SettingKey) -> SettingKeyRegistry:
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

        return self

    def unregister(self, *skeys: _SettingKey) -> SettingKeyRegistry:
        pop = self._skeys.pop

        for skey in skeys:
            if pop(skey.id, None) is None:
                raise self.RegistrationError(
                    f'This Setting is not registered (already un-registered ?): {skey.id}'
                )

        return self


setting_key_registry = SettingKeyRegistry(SettingKey)
user_setting_key_registry = SettingKeyRegistry(UserSettingKey)


# def __getattr__(name):
#     if name == '_SettingKeyRegistry':
#         warnings.warn(
#             '"_SettingKeyRegistry" is deprecated; use "SettingKeyRegistry" instead.',
#             DeprecationWarning,
#         )
#         return SettingKeyRegistry
#
#     raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


class UserSettingValueManager:
    """Manager related to a user which can read & write setting values stored
    in a TextField (serialized to JSON).
    See the property <creme_core.models.CremeUser.settings>.
    """
    class ReadOnlyError(Exception):
        pass

    def __init__(self, user_class: type[Model], user_id, json_settings: TextField):
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
                'changes will not be saved!'
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
