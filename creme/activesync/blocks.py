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

#from django.utils.translation import ugettext_lazy as _

from creme.creme_core.gui.block import Block, QuerysetBlock

from creme.creme_config.models.setting import SettingValue

from creme.persons.models.contact import Contact

from .models.active_sync import (UserSynchronizationHistory,
        USER_HISTORY_TYPE_VERBOSE, USER_HISTORY_WHERE_VERBOSE)
from .constants import (USER_MOBILE_SYNC_SERVER_URL, MAPI_SERVER_URL,
        USER_MOBILE_SYNC_SERVER_DOMAIN, MAPI_DOMAIN,
        USER_MOBILE_SYNC_SERVER_SSL, MAPI_SERVER_SSL,
        USER_MOBILE_SYNC_SERVER_LOGIN, USER_MOBILE_SYNC_SERVER_PWD,
        USER_MOBILE_SYNC_ACTIVITIES, USER_MOBILE_SYNC_CONTACTS)


class UserMobileSyncConfigBlock(Block):
    id_           = Block.generate_id('activesync', 'user_mobile_sync')
    #dependencies  = ()
    verbose_name  = u'Mobile synchronization configuration for a user'
    template_name = 'activesync/templatetags/block_user_mobile_sync.html'
    configurable  = False
    permission    = None

    def detailview_display(self, context):
        #request = context.get('request')
        request = context['request']

        #undefined = _(u"Undefined")
        #default   = _(u"Default configuration")
        #yes   = _(u"Yes")
        #no    = _(u"No")

        #url      = undefined
        #domain   = undefined
        #ssl      = undefined
        #username = undefined
        #password = ""
        #sync_cal = undefined
        #sync_con = undefined

        #if request:
        user   = request.user
        sv_get = SettingValue.objects.get

        def get_setting_value(user_key, default_key=None):
            svalue = None

            try:
                svalue = sv_get(key__id=user_key, user=user)
            except SettingValue.DoesNotExist:
                if default_key:
                    #try:
                        svalue = sv_get(key__id=default_key)
                    #except SettingValue.DoesNotExist:
                        #pass
                    #else:
                        svalue.default_config = True
            else:
                svalue.default_config = False

            return svalue

            #try:
                #url = sv_get(key__id=USER_MOBILE_SYNC_SERVER_URL, user=user).value
            #except SettingValue.DoesNotExist:
                #try:
                    #url = u"%s (%s)" % (sv_get(key__id=MAPI_SERVER_URL).value, default)
                #except SettingValue.DoesNotExist:
                    #pass
        url = get_setting_value(USER_MOBILE_SYNC_SERVER_URL, MAPI_SERVER_URL)

            #try:
                #domain = sv_get(key__id=USER_MOBILE_SYNC_SERVER_DOMAIN, user=user).value
            #except SettingValue.DoesNotExist:
                #try:
                    #domain = u"%s (%s)" % (sv_get(key__id=MAPI_DOMAIN).value, default)
                #except SettingValue.DoesNotExist:
                    #pass
        domain = get_setting_value(USER_MOBILE_SYNC_SERVER_DOMAIN, MAPI_DOMAIN)

            #try:
                #ssl = sv_get(key__id=USER_MOBILE_SYNC_SERVER_SSL, user=user).value
            #except SettingValue.DoesNotExist:
                #try:
                    #ssl = u"%s (%s)" % (yes if sv_get(key__id=MAPI_SERVER_SSL).value else no, default)
                #except SettingValue.DoesNotExist:
                    #pass
        ssl = get_setting_value(USER_MOBILE_SYNC_SERVER_SSL, MAPI_SERVER_SSL)

            #try:
                #username = sv_get(key__id=USER_MOBILE_SYNC_SERVER_LOGIN, user=user).value
            #except SettingValue.DoesNotExist:
                #pass
        username = get_setting_value(USER_MOBILE_SYNC_SERVER_LOGIN)

            #try:
                #password = sv_get(key__id=USER_MOBILE_SYNC_SERVER_PWD, user=user).value
            #except SettingValue.DoesNotExist:
                #pass
        #TODO: It's the ciphered value but it's just for display. Is it a problem ?
        password = get_setting_value(USER_MOBILE_SYNC_SERVER_PWD)

            #try:
                #sync_cal = sv_get(key__id=USER_MOBILE_SYNC_ACTIVITIES, user=user).value
            #except SettingValue.DoesNotExist:
                #pass
        sync_cal = get_setting_value(USER_MOBILE_SYNC_ACTIVITIES)

            #try:
                #sync_con = sv_get(key__id=USER_MOBILE_SYNC_CONTACTS, user=user).value
            #except SettingValue.DoesNotExist:
                #pass
        sync_con = get_setting_value(USER_MOBILE_SYNC_CONTACTS)

        return self._render(self.get_block_template_context(context,
                                                            url=url,
                                                            domain=domain,
                                                            ssl=ssl,
                                                            username=username,
                                                            password=password,
                                                            sync_cal=sync_cal,
                                                            sync_con=sync_con,
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                                           )
                           )


class MobileSyncConfigBlock(Block):
    id_           = Block.generate_id('activesync', 'mobile_sync_config')
    dependencies  = ()
    verbose_name  = u'Mobile synchronization configuration'
    template_name = 'activesync/templatetags/block_mobile_sync_config.html'
    configurable  = False
    permission    = 'activesync.can_admin'

    def detailview_display(self, context):
        sv_get = SettingValue.objects.get

        #Nb: Those values had been populated
        #server_url    = sv_get(key__id=MAPI_SERVER_URL).value
        #server_domain = sv_get(key__id=MAPI_DOMAIN).value
        #server_ssl    = sv_get(key__id=MAPI_SERVER_SSL).value
        server_url    = sv_get(key__id=MAPI_SERVER_URL)
        server_domain = sv_get(key__id=MAPI_DOMAIN)
        server_ssl    = sv_get(key__id=MAPI_SERVER_SSL)

        return self._render(self.get_block_template_context(context,
                                                            url=server_url,
                                                            domain=server_domain,
                                                            ssl=server_ssl,
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                                           )
                           )


class UserSynchronizationHistoryBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('activesync', 'user_synchronization_history')
    dependencies  = (UserSynchronizationHistory,)
    verbose_name  = u'User synchronization history'
    template_name = 'activesync/templatetags/block_user_synchronization_history.html'
    configurable  = False
    order_by      = '-created'

    def detailview_display(self, context):
        user = context['user']
        btc = self.get_block_template_context(context,
                                              UserSynchronizationHistory.objects.filter(user=user)
                                                                                .select_related('entity_ct'),
                                              history_type_verbose=USER_HISTORY_TYPE_VERBOSE,
                                              history_where_verbose=USER_HISTORY_WHERE_VERBOSE,
                                              contact_klass=Contact,
                                              update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, user.pk),
                                             )

        history = btc['page'].object_list
        UserSynchronizationHistory.populate_entities(history)

        return self._render(btc)


user_mobile_sync_config_block      = UserMobileSyncConfigBlock()
mobile_sync_config_block           = MobileSyncConfigBlock()
user_synchronization_history_block = UserSynchronizationHistoryBlock()
