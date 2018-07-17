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

from json import dumps as jsondumps, loads as jsonloads
import logging

from django.utils.translation import ugettext as _

from ..utils import bool_from_str, bool_as_html


logger = logging.getLogger(__name__)


# TODO: move to utils ?
def print_hour(value):
    return _('{hour}h').format(hour=value)


class _SettingKey:
    STRING = 1
    INT    = 2
    BOOL   = 3
    HOUR   = 10
    EMAIL  = 20

    _CASTORS = {
            STRING: str,
            INT:    int,
            BOOL:   bool_from_str,
            HOUR:   int,  # TODO: validate 0 =< x =< 23  ??
            EMAIL:  str,
        }

    HTML_PRINTERS = {
            BOOL:   bool_as_html,
            HOUR:   print_hour,
        }

    def __init__(self, id, description, app_label, type=STRING, hidden=False, blank=False):
        """Constructor.
        @param id: Unique String. Use something like 'my_app-key_name'
        @param description: Used in the configuration GUI ; use a ugettext_lazy() instance ('' is OK if hidden==True)
        @param app_label: Eg: 'creme_core'
        @param type: Integer ; see: _SettingKey.STRING, _SettingKey.INT ...
        @param hidden: Boolean. If True, It can not be seen in the configuration GUI.
        """
        self.id          = id
        self.description = description
        self.app_label   = app_label
        self.type        = type
        self.hidden      = hidden
        self.blank       = blank

        self._castor = self._CASTORS[type]

    def __str__(self):
        return u'{cls}(id="{id}", description="{description}", ' \
               u'app_label="{app_label}", type={type}, hidden={hidden})'.format(
                cls=self.__class__.__name__,
                id=self.id,
                description=self.description,
                app_label=self.app_label,
                type=self.type,
                hidden=self.hidden,
        )

    def cast(self, value_str):
        return self._castor(value_str)

    def value_as_html(self, value):
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
            # _SettingKey.BOOL:   bool_from_str,
            _SettingKey.BOOL:   bool,  # TODO: fix _SettingKey to use JSON ('True' => 'true') ??
            _SettingKey.HOUR:   int,
            _SettingKey.EMAIL:  str,
        }


class _SettingKeyRegistry:
    class RegistrationError(Exception):
        pass

    def __init__(self, key_class=SettingKey):
        self._skeys = {}
        self._key_class = key_class

    def __getitem__(self, key_id):
        return self._skeys[key_id]

    def __iter__(self):
        return iter(self._skeys.values())

    def register(self, *skeys):
        setdefault = self._skeys.setdefault
        key_class = self._key_class

        for skey in skeys:
            if not isinstance(skey, key_class):
                raise self.RegistrationError("Bad class for key {} (need {})".format(skey, key_class))

            if setdefault(skey.id, skey) is not skey:
                raise self.RegistrationError("Duplicated setting key's id: {}".format(skey.id))

    def unregister(self, *skeys):
        pop = self._skeys.pop

        for skey in skeys:
            if pop(skey.id, None) is None:
                # logger.warn('This Setting is not registered (already un-registered ?): %s', skey.id)
                raise self.RegistrationError('This Setting is not registered '
                                             '(already un-registered ?): {}'.format(skey.id)
                                            )


setting_key_registry = _SettingKeyRegistry(SettingKey)
user_setting_key_registry = _SettingKeyRegistry(UserSettingKey)


class UserSettingValueManager:
    class ReadOnlyError(Exception):
        pass

    def __init__(self, user_class, user_id, json_settings):
        self._user_class = user_class
        self._user_id = user_id
        self._values = jsonloads(json_settings)
        self._read_only = True

    def __enter__(self):
        self._read_only = False

        return self

    def __exit__(self, exc_type, exc_value, tb):
        self._read_only = True

        if exc_value:
            # TODO: do we need a non-atomic mode which saves anyway ?
            logger.warning('UserSettingValueManager: an exception has been raised, changes will not be saved !')
            raise exc_value

        self._user_class.objects.filter(pk=self._user_id)\
                                .update(json_settings=jsondumps(self._values))

        return True

    def __getitem__(self, key):
        "@raise KeyError"
        return key.cast(self._values[key.id])

    # TODO: accept key or key_id ??
    def __setitem__(self, key, value):
        if self._read_only:
            raise self.ReadOnlyError

        casted_value = key.cast(value)
        self._values[key.id] = casted_value

        return casted_value

    def __delitem__(self, key):
        self.pop(key)

    def as_html(self, key):
        return key.value_as_html(self[key])

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def pop(self, key, *default):
        if self._read_only:
            raise self.ReadOnlyError

        return self._values.pop(key.id, *default)

    # TODO:  __contains__ ??
