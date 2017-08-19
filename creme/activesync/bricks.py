# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2017  Hybird
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

from django.conf import settings
from django.core.urlresolvers import reverse

from creme.creme_core.gui.bricks import Brick, QuerysetBrick
# from creme.creme_core.models import SettingValue

from creme.persons import get_contact_model

from .models.active_sync import (UserSynchronizationHistory,
        USER_HISTORY_TYPE_VERBOSE, USER_HISTORY_WHERE_VERBOSE)
# from .constants import (MAPI_SERVER_URL, MAPI_DOMAIN, MAPI_SERVER_SSL,
#         USER_MOBILE_SYNC_SERVER_DOMAIN, USER_MOBILE_SYNC_SERVER_URL,
#         USER_MOBILE_SYNC_SERVER_SSL,
#         USER_MOBILE_SYNC_SERVER_LOGIN, USER_MOBILE_SYNC_SERVER_PWD,
#         USER_MOBILE_SYNC_ACTIVITIES, USER_MOBILE_SYNC_CONTACTS)
from . import setting_keys
from .utils import get_default_server_setting_values


logger = logging.getLogger(__name__)


class UserMobileSyncConfigBrick(Brick):
    id_           = Brick.generate_id('activesync', 'user_mobile_sync')
    verbose_name  = u'Mobile synchronization configuration for a user'
    # template_name = 'activesync/templatetags/block_user_mobile_sync.html'
    template_name = 'activesync/bricks/user-config.html'
    configurable  = False
    permission    = None

    def detailview_display(self, context):
        user = context['user']
        user_settings = user.settings
        # sv_get = SettingValue.objects.get
        default_values = {}

        # def get_setting_value(user_key_id, default_key_id=None):
        #     svalue = None
        #
        #     try:
        #         svalue = sv_get(key_id=user_key_id, user=user)
        #     except SettingValue.DoesNotExist:
        #         if default_key_id:
        #             try:
        #                 svalue = sv_get(key_id=default_key_id)
        #             except SettingValue.DoesNotExist:
        #                 logger.warn('Activesync.UserMobileSyncConfigBlock: unfoundable SettingValue(key="%s") '
        #                             '- Populate has not been run ?! (if you are running unit tests you can '
        #                             'ignore this message' % default_key_id
        #                            )  # NB useful for creme_config tests
        #             else:
        #                 svalue.default_config = True
        #     else:
        #         svalue.default_config = False
        #
        #     return svalue
        def get_setting_value(user_skey, default_key=None):
            # html_value = None
            default_config = False

            try:
                html_value = user_settings.as_html(user_skey)
            except KeyError:
                if not default_key:
                    return None

                # TODO: use nonlocal in py3 instead...
                if not default_values:
                    default_values.update(get_default_server_setting_values())

                html_value = default_values[default_key].as_html
                default_config = True

            return {'as_html': html_value, 'default_config': default_config}

        # return self._render(self.get_block_template_context(
        return self._render(self.get_template_context(
                    context,
                    # url=get_setting_value(USER_MOBILE_SYNC_SERVER_URL, MAPI_SERVER_URL),
                    # domain=get_setting_value(USER_MOBILE_SYNC_SERVER_DOMAIN, MAPI_DOMAIN),
                    # ssl=get_setting_value(USER_MOBILE_SYNC_SERVER_SSL, MAPI_SERVER_SSL),
                    # username=get_setting_value(USER_MOBILE_SYNC_SERVER_LOGIN),
                    # password=get_setting_value(USER_MOBILE_SYNC_SERVER_PWD),
                    # sync_cal=get_setting_value(USER_MOBILE_SYNC_ACTIVITIES),
                    # sync_con=get_setting_value(USER_MOBILE_SYNC_CONTACTS),
                    url=get_setting_value(setting_keys.user_msync_server_url_key, 'url'),
                    domain=get_setting_value(setting_keys.user_msync_server_domain_key, 'domain'),
                    ssl=get_setting_value(setting_keys.user_msync_server_ssl_key, 'ssl'),
                    username=get_setting_value(setting_keys.user_msync_server_login_key),
                    # TODO: It's the ciphered value but it's just for display. Is it a problem ?
                    password=get_setting_value(setting_keys.user_msync_server_pwd_key),
                    sync_cal=get_setting_value(setting_keys.user_msync_activities_key),
                    sync_con=get_setting_value(setting_keys.user_msync_contacts_key),
                    # update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                    update_url=reverse('creme_core__reload_blocks', args=(self.id_,)),
        ))


class MobileSyncConfigBrick(Brick):
    id_           = Brick.generate_id('activesync', 'mobile_sync_config')
    # dependencies  = ()
    verbose_name  = u'Mobile synchronization configuration'
    # template_name = 'activesync/templatetags/block_mobile_sync_config.html'
    template_name = 'activesync/bricks/default-config.html'
    configurable  = False
    permission    = 'activesync.can_admin'

    def detailview_display(self, context):
        # sv_get = SettingValue.objects.get
        # server_url    = sv_get(key_id=MAPI_SERVER_URL)
        # server_domain = sv_get(key_id=MAPI_DOMAIN)
        # server_ssl    = sv_get(key_id=MAPI_SERVER_SSL)
        values = get_default_server_setting_values()

        # return self._render(self.get_block_template_context(
        return self._render(self.get_template_context(
                    context,
                    # url=server_url,
                    # domain=server_domain,
                    # ssl=server_ssl,
                    url=values['url'],
                    domain=values['domain'],
                    ssl=values['ssl'],
                    # update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                    update_url=reverse('creme_core__reload_blocks', args=(self.id_,)),
        ))


class UserSynchronizationParametersBrick(Brick):
    id_           = Brick.generate_id('activesync', 'user_synchronization_parameters')
    dependencies = (UserSynchronizationHistory,)
    verbose_name  = u'User synchronization parameters'
    template_name = 'activesync/bricks/sync-parameters.html'
    configurable  = False

    def __init__(self, sync):
        """Constructor
        @param sync:  activesync.sync.Synchronization instance, or None (which means 'fatal sync error')
        """
        super(UserSynchronizationParametersBrick, self).__init__()
        self.sync = sync

    def detailview_display(self, context):
        return self._render(self.get_template_context(
                    context,
                    sync=self.sync,
        ))


class UserSynchronizationDebugBrick(Brick):
    id_           = Brick.generate_id('activesync', 'user_synchronization_debug')
    dependencies = (UserSynchronizationHistory,)
    verbose_name  = u'User synchronization DEBUG'
    template_name = 'activesync/bricks/sync-debug.html'
    configurable  = False

    def __init__(self, sync):
        super(UserSynchronizationDebugBrick, self).__init__()
        self.debug_data = sync._data['debug']

    def detailview_display(self, context):
        debug = settings.ACTIVE_SYNC_DEBUG

        if debug:
            debug_data = self.debug_data
            xml = debug_data['xml']
            debug_info = debug_data['info']
            debug_errors = debug_data['errors']
        else:
            xml = debug_info = debug_errors = None

        return self._render(self.get_template_context(
                    context,
                    ACTIVE_SYNC_DEBUG=debug,
                    xml=xml,
                    debug_info=debug_info,
                    debug_errors=debug_errors,
        ))


class UserSynchronizationResultsBrick(Brick):
    id_           = Brick.generate_id('activesync', 'user_synchronization_results')
    dependencies  = (UserSynchronizationHistory,)
    verbose_name  = u'User synchronization results'
    template_name = 'activesync/bricks/sync-results.html'
    configurable  = False

    def __init__(self, sync=None, messages=None):
        super(UserSynchronizationResultsBrick, self).__init__()
        self.messages = messages or sync.messages()

    def detailview_display(self, context):
        return self._render(self.get_template_context(context, all_messages=self.messages))


class UserSynchronizationHistoryBrick(QuerysetBrick):
    id_           = QuerysetBrick.generate_id('activesync', 'user_synchronization_history')
    dependencies  = (UserSynchronizationHistory,)
    verbose_name  = u'User synchronization history'
    # template_name = 'activesync/templatetags/block_user_synchronization_history.html'
    template_name = 'activesync/bricks/sync-history.html'
    configurable  = False
    order_by      = '-created'

    def detailview_display(self, context):
        btc = self.get_template_context(
                    context,
                    UserSynchronizationHistory.objects.filter(user=context['user'])
                                                      .select_related('entity_ct'),
                    history_type_verbose=USER_HISTORY_TYPE_VERBOSE,
                    history_where_verbose=USER_HISTORY_WHERE_VERBOSE,
                    contact_klass=get_contact_model(),  # TODO: use {% ctype_for_swappable ... %} instead
        )

        history = btc['page'].object_list
        UserSynchronizationHistory.populate_entities(history)

        return self._render(btc)
