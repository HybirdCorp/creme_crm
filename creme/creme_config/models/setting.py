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
from django.db.models import (Model, CharField, TextField,
        PositiveSmallIntegerField, BooleanField, ForeignKey)

from creme.creme_core.utils import bool_from_str


class SettingKey(Model):
    id          = CharField(primary_key=True, max_length=100)
    description = TextField()
    app_label   = CharField(max_length=100, blank=True, null=True)
    type        = PositiveSmallIntegerField()
    hidden      = BooleanField(default=False)

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

    class Meta:
        app_label = "creme_config"

    def cast(self, value_str):
        return self._CASTORS[self.type](value_str)

    @staticmethod
    def create(pk, description, app_label, type, hidden=False):
        from creme.creme_core.utils import create_or_update

        sk = create_or_update(SettingKey, pk=pk, description=description,
                              app_label=app_label, type=type, hidden=hidden,
                             )
        #sk.settingvalue_set.all().delete()

        return sk

#TODO: Add a null and blank attribute ?? And a unique together with key, user
class SettingValue(Model):
    key       = ForeignKey(SettingKey)
    user      = ForeignKey(User, blank=True, null=True)
    value_str = TextField()

    class Meta:
        app_label = "creme_config"

    @property
    def value(self):
        return self.key.cast(self.value_str)

    @value.setter
    def value(self, value):
        self.value_str = str(value)

    @staticmethod
    def create_if_needed(key, user, value):
        #try:
            #sv = SettingValue.objects.get(key=key, user=user)
        #except SettingValue.DoesNotExist:
            #sv = SettingValue.objects.create(key=key, user=user, value=value)

        #return sv
        return SettingValue.objects.get_or_create(key=key, user=user,
                                                  defaults={'value': value},
                                                 )[0]
