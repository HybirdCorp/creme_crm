# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.utils.translation import ugettext_lazy as _

from creme_core.gui.block import Block

from creme_config.models.setting import SettingValue

from activesync.constants import (USER_MOBILE_SYNC_SERVER_URL, MAPI_SERVER_URL, USER_MOBILE_SYNC_SERVER_DOMAIN,
                                  MAPI_DOMAIN, USER_MOBILE_SYNC_SERVER_SSL, MAPI_SERVER_SSL,
                                  USER_MOBILE_SYNC_SERVER_LOGIN, USER_MOBILE_SYNC_SERVER_PWD
                                  )

class UserMobileSyncConfigBlock(Block):
    id_           = Block.generate_id('activesync', 'user_mobile_sync')
    dependencies  = ()
    verbose_name  = _(u'Mobile synchronization')
    template_name = 'activesync/templatetags/block_user_mobile_sync.html'
    permission    = None
    
    def detailview_display(self, context):
        request = context.get('request')

        undefined = _(u"Undefined")
        default   = _(u"Default configuration")

        url      = undefined
        domain   = undefined
        ssl      = undefined
        username = undefined
        password = ""
        
        if request:
            user    = request.user

            sv_get = SettingValue.objects.get

            try:
                url = sv_get(key__id=USER_MOBILE_SYNC_SERVER_URL, user=user).value
            except SettingValue.DoesNotExist:
                try:
                    url = u"%s (%s)" % (sv_get(key__id=MAPI_SERVER_URL).value, default)
                except SettingValue.DoesNotExist:
                    pass

            try:
                domain = sv_get(key__id=USER_MOBILE_SYNC_SERVER_DOMAIN, user=user).value
            except SettingValue.DoesNotExist:
                try:
                    domain = u"%s (%s)" % (sv_get(key__id=MAPI_DOMAIN).value, default)
                except SettingValue.DoesNotExist:
                    pass

            try:
                ssl = sv_get(key__id=USER_MOBILE_SYNC_SERVER_SSL, user=user).value
            except SettingValue.DoesNotExist:
                try:
                    ssl = u"%s (%s)" % (sv_get(key__id=MAPI_SERVER_SSL).value, default)
                except SettingValue.DoesNotExist:
                    pass

            try:
                username = sv_get(key__id=USER_MOBILE_SYNC_SERVER_LOGIN, user=user).value
            except SettingValue.DoesNotExist:
                pass

            try:
                password = sv_get(key__id=USER_MOBILE_SYNC_SERVER_PWD, user=user).value
            except SettingValue.DoesNotExist:
                pass


        return self._render(self.get_block_template_context(context,
                                                            url=url,
                                                            domain=domain,
                                                            ssl=ssl,
                                                            username=username,
                                                            password=password,
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,))

class MobileSyncConfigBlock(Block):
    id_           = Block.generate_id('activesync', 'mobile_sync_config')
    dependencies  = ()
    verbose_name  = _(u'Mobile synchronization')
    template_name = 'activesync/templatetags/block_mobile_sync_config.html'
    permission    = 'activesync.can_admin'

    def detailview_display(self, context):

        sv_get = SettingValue.objects.get

        #Nb: Those values had been populated
        server_url    = sv_get(key__id=MAPI_SERVER_URL).value
        server_domain = sv_get(key__id=MAPI_DOMAIN).value
        server_ssl    = sv_get(key__id=MAPI_SERVER_SSL).value

        return self._render(self.get_block_template_context(context,
                                                            url=server_url,
                                                            domain=server_domain,
                                                            ssl=server_ssl,
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,))


user_mobile_sync_config_block = UserMobileSyncConfigBlock()
mobile_sync_config_block      = MobileSyncConfigBlock()
