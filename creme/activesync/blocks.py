# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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

#from django.utils.translation import ugettext_lazy as _

from creme.creme_core.gui.block import Block, QuerysetBlock
from creme.creme_core.models import SettingValue

from creme.persons import get_contact_model
#from creme.persons.models.contact import Contact

from .models.active_sync import (UserSynchronizationHistory,
        USER_HISTORY_TYPE_VERBOSE, USER_HISTORY_WHERE_VERBOSE)
from .constants import (USER_MOBILE_SYNC_SERVER_URL, MAPI_SERVER_URL,
        USER_MOBILE_SYNC_SERVER_DOMAIN, MAPI_DOMAIN,
        USER_MOBILE_SYNC_SERVER_SSL, MAPI_SERVER_SSL,
        USER_MOBILE_SYNC_SERVER_LOGIN, USER_MOBILE_SYNC_SERVER_PWD,
        USER_MOBILE_SYNC_ACTIVITIES, USER_MOBILE_SYNC_CONTACTS)


logger = logging.getLogger(__name__)


class UserMobileSyncConfigBlock(Block):
    id_           = Block.generate_id('activesync', 'user_mobile_sync')
    verbose_name  = u'Mobile synchronization configuration for a user'
    template_name = 'activesync/templatetags/block_user_mobile_sync.html'
    configurable  = False
    permission    = None

    def detailview_display(self, context):
        request = context['request']
        user   = request.user
        sv_get = SettingValue.objects.get

        def get_setting_value(user_key_id, default_key_id=None):
            svalue = None

            try:
                svalue = sv_get(key_id=user_key_id, user=user)
            except SettingValue.DoesNotExist:
                if default_key_id:
                    try:
                        svalue = sv_get(key_id=default_key_id)
                    except SettingValue.DoesNotExist:
                        logger.warn('Activesync.UserMobileSyncConfigBlock: unfoundable SettingValue(key="%s") '
                                    '- Populate has not been runned ?! (if you are running unit tests you can '
                                    'ignore this message' % default_key_id
                                   ) # NB useful for creme_config tests
                    else:
                        svalue.default_config = True
            else:
                svalue.default_config = False

            return svalue

        return self._render(self.get_block_template_context(
                                context,
                                url=get_setting_value(USER_MOBILE_SYNC_SERVER_URL, MAPI_SERVER_URL),
                                domain=get_setting_value(USER_MOBILE_SYNC_SERVER_DOMAIN, MAPI_DOMAIN),
                                ssl=get_setting_value(USER_MOBILE_SYNC_SERVER_SSL, MAPI_SERVER_SSL),
                                username=get_setting_value(USER_MOBILE_SYNC_SERVER_LOGIN),
                                # TODO: It's the ciphered value but it's just for display. Is it a problem ?
                                password=get_setting_value(USER_MOBILE_SYNC_SERVER_PWD),
                                sync_cal=get_setting_value(USER_MOBILE_SYNC_ACTIVITIES),
                                sync_con=get_setting_value(USER_MOBILE_SYNC_CONTACTS),
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
        # TODO: group queries ?? hand made VS something like
        # SettingValue.objects.bulk_per_keys(url=MAPI_SERVER_URL, domain=MAPI_DOMAIN)
        #   => {'url': ..., 'domain': ...}   (as **kwargs for get_block_template_context())
        sv_get = SettingValue.objects.get
        server_url    = sv_get(key_id=MAPI_SERVER_URL)
        server_domain = sv_get(key_id=MAPI_DOMAIN)
        server_ssl    = sv_get(key_id=MAPI_SERVER_SSL)

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
#                                              contact_klass=Contact,
                                              contact_klass=get_contact_model(),
                                              update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, user.pk),
                                             )

        history = btc['page'].object_list
        UserSynchronizationHistory.populate_entities(history)

        return self._render(btc)


user_mobile_sync_config_block      = UserMobileSyncConfigBlock()
mobile_sync_config_block           = MobileSyncConfigBlock()
user_synchronization_history_block = UserSynchronizationHistoryBlock()
