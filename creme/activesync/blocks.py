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
from creme_core.models import *
from creme_core.templatetags.creme_core_tags import print_boolean

from creme_config.constants import *
from creme_config.models.config_models import CremeKVConfig


class UserMobileSyncConfigBlock(Block):
    id_           = Block.generate_id('activesync', 'user_mobile_sync')
    dependencies  = ()
    verbose_name  = _(u'Mobile synchronization')
    template_name = 'activesync/templatetags/block_user_mobile_sync.html'

    def detailview_display(self, context):
        request = context.get('request')

        undefined = _(u"Undefined")
        default   = _(u"Default configuration")

        url      = undefined
        domain   = undefined
        ssl      = undefined
        username = undefined
        password = undefined
        
        if request:
            user    = request.user
            user_id = user.id

            ckv_get = CremeKVConfig.objects.get

            try:
                url = ckv_get(pk=USER_MOBILE_SYNC_SERVER_URL % user_id).value
            except CremeKVConfig.DoesNotExist:
                try:
                    url = u"%s (%s)" % (ckv_get(pk=MAPI_SERVER_URL).value, default)
                except CremeKVConfig.DoesNotExist:
                    pass

            try:
                domain = ckv_get(pk=USER_MOBILE_SYNC_SERVER_DOMAIN % user_id).value
            except CremeKVConfig.DoesNotExist:
                try:
                    domain = u"%s (%s)" % (ckv_get(pk=MAPI_DOMAIN).value, default)
                except CremeKVConfig.DoesNotExist:
                    pass

            try:
                ssl = print_boolean(bool(int(ckv_get(pk=USER_MOBILE_SYNC_SERVER_SSL % user_id).value)))
            except CremeKVConfig.DoesNotExist:
                try:
                    ssl = u"%s (%s)" % (print_boolean(bool(int(ckv_get(pk=MAPI_SERVER_SSL).value))), default)
                except CremeKVConfig.DoesNotExist:
                    pass

            try:
                username = ckv_get(pk=USER_MOBILE_SYNC_SERVER_LOGIN % user_id).value
            except CremeKVConfig.DoesNotExist:
                pass

            try:
                password = ckv_get(pk=USER_MOBILE_SYNC_SERVER_PWD % user_id).value
            except CremeKVConfig.DoesNotExist:
                pass


        return self._render(self.get_block_template_context(context,
                                                            url=url,
                                                            domain=domain,
                                                            ssl=ssl,
                                                            username=username,
                                                            password=password,
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,))

user_mobile_sync_config_block = UserMobileSyncConfigBlock()
