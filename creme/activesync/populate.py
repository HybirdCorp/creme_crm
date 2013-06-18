# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from creme.creme_core.management.commands.creme_populate import BasePopulator

from creme.creme_config.models import SettingKey, SettingValue

from .constants import (MAPI_DOMAIN, MAPI_SERVER_SSL, MAPI_SERVER_URL, USER_MOBILE_SYNC_SERVER_URL,
                        USER_MOBILE_SYNC_SERVER_DOMAIN, USER_MOBILE_SYNC_SERVER_SSL,
                        USER_MOBILE_SYNC_SERVER_LOGIN, USER_MOBILE_SYNC_SERVER_PWD,
                        USER_MOBILE_SYNC_ACTIVITIES, USER_MOBILE_SYNC_CONTACTS)


class Populator(BasePopulator):
    def populate(self):
        sk = SettingKey.create(pk=MAPI_SERVER_URL,
                               description="", hidden=True,
                               app_label='activesync', type=SettingKey.STRING
                              )
        SettingValue.create_if_needed(key=sk, user=None, value="")

        sk = SettingKey.create(pk=MAPI_DOMAIN,
                               description="", hidden=True,
                               app_label='activesync', type=SettingKey.STRING
                              )
        SettingValue.create_if_needed(key=sk, user=None, value="")

        sk = SettingKey.create(pk=MAPI_SERVER_SSL,
                               description="", hidden=True,
                               app_label='activesync', type=SettingKey.BOOL
                              )
        SettingValue.create_if_needed(key=sk, user=None, value=False)

        SettingKey.create(pk=USER_MOBILE_SYNC_SERVER_URL,
                          description="", hidden=True,
                          app_label='activesync', type=SettingKey.STRING
                         )
        SettingKey.create(pk=USER_MOBILE_SYNC_SERVER_DOMAIN,
                          description="", hidden=True,
                          app_label='activesync', type=SettingKey.STRING
                         )
        SettingKey.create(pk=USER_MOBILE_SYNC_SERVER_SSL,
                          description="", hidden=True,
                          app_label='activesync', type=SettingKey.BOOL
                         )
        SettingKey.create(pk=USER_MOBILE_SYNC_SERVER_LOGIN,
                          description="", hidden=True,
                          app_label='activesync', type=SettingKey.STRING
                         )
        SettingKey.create(pk=USER_MOBILE_SYNC_SERVER_PWD,
                          description="", hidden=True,
                          app_label='activesync', type=SettingKey.STRING
                         )
        SettingKey.create(pk=USER_MOBILE_SYNC_ACTIVITIES,
                          description="", hidden=True,
                          app_label='activesync', type=SettingKey.BOOL
                         )
        SettingKey.create(pk=USER_MOBILE_SYNC_CONTACTS,
                          description="", hidden=True,
                          app_label='activesync', type=SettingKey.BOOL
                         )
