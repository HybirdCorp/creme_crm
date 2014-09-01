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

from .. import autodiscover
from ..registry import creme_registry, NotRegistered as AppNotRegistered
from ..utils import bool_from_str


class SettingKey(object):
    STRING = 1
    INT    = 2
    BOOL   = 3
    HOUR   = 10

    _CASTORS = {
            STRING: unicode,
            INT:    int,
            BOOL:   bool_from_str,
            HOUR:   int, #TODO: validate 0 =< x =< 23  ??
        }

    def __init__(self, id, description, app_label, type=STRING, hidden=False):
        """Constructor.
        @param id Unique String. Use something like 'my_app-key_name'
        @param description Used in the configuration GUI ; use a ugettext_lazy() instance ('' is OK if hidden==True)
        @param app_label Eg: 'creme_core'
        @param type Integer ; see: SettingKey.STRING, SettingKey.INT ...
        @param hidden Boolean. If True, It can not be seen in the configuration GUI.
        """
        self.id          = id
        self.description = description
        self.app_label   = app_label
        self.type        = type
        self.hidden      = hidden

        self._castor = self._CASTORS[type]

    def cast(self, value_str):
        return self._castor(value_str)


class _SettingKeyRegistry(object):
    class RegistrationError(Exception):
        pass

    def __init__(self):
        self._skeys = {}

    def _get_keys(self):
        #  __getitem__ is sometimes called during the "populate" scripts are running
        # so autodiscover() has not been called (so SettingKey are not registered)
        # TODO: call autodiscover() in populate scripts ??
        try:
            creme_registry.get_app('creme_config')
        except AppNotRegistered:
            autodiscover()

        return self._skeys

    def __getitem__(self, key_id): #TODO: Exception
        return self._get_keys()[key_id]

    def __iter__(self):
        return self._get_keys().itervalues()

    def register(self, *skeys):
        setdefault = self._get_keys().setdefault

        for skey in skeys:
            if setdefault(skey.id, skey) is not skey:
                raise _SettingKeyRegistry.RegistrationError("Duplicated setting key's id: %s" % skey.id)


setting_key_registry = _SettingKeyRegistry()
