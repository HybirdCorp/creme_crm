# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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
from django.contrib.contenttypes.models import ContentType

from creme_core.management.commands.creme_populate import BasePopulator
#from creme_core.utils import create_or_update_models_instance as create

from creme_config.constants import USER_SETTINGS_BLOCK_PREFIX
from creme_config.models.setting import SettingKey, SettingValue

from activesync.constants import (MAPI_DOMAIN, MAPI_SERVER_SSL, MAPI_SERVER_URL, USER_MOBILE_SYNC_SERVER_URL,
                                  USER_MOBILE_SYNC_SERVER_DOMAIN, USER_MOBILE_SYNC_SERVER_SSL,
                                  USER_MOBILE_SYNC_SERVER_LOGIN, USER_MOBILE_SYNC_SERVER_PWD)


class Populator(BasePopulator):
    def populate(self, *args, **kwargs):
        sk_mapi_server_url = SettingKey.create(pk=MAPI_SERVER_URL,
                       description="", hidden=True,
                       app_label='activesync', type=SettingKey.STRING
                       )
        SettingValue.objects.create(key=sk_mapi_server_url, user=None, value="")

        sk_mapi_domain = SettingKey.create(pk=MAPI_DOMAIN,
                       description="", hidden=True,
                       app_label='activesync', type=SettingKey.STRING
                       )
        SettingValue.objects.create(key=sk_mapi_domain, user=None, value="")

        sk_mapi_ssl = SettingKey.create(pk=MAPI_SERVER_SSL,
                       description="", hidden=True,
                       app_label='activesync', type=SettingKey.BOOL
                       )
        SettingValue.objects.create(key=sk_mapi_ssl, user=None, value=False)

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
