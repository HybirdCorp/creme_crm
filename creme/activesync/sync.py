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

from collections import defaultdict

from django.conf import settings
from django.core import validators
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

# from creme.creme_core.models import SettingValue

from . import constants as as_constants
from . import setting_keys
from .cipher import Cipher
from .commands import FolderSync, Provision, AirSync
# from .constants import (MAPI_DOMAIN, MAPI_SERVER_SSL, MAPI_SERVER_URL,
#         USER_MOBILE_SYNC_SERVER_DOMAIN, USER_MOBILE_SYNC_SERVER_LOGIN,
#         USER_MOBILE_SYNC_SERVER_PWD, USER_MOBILE_SYNC_SERVER_SSL, USER_MOBILE_SYNC_SERVER_URL)
from .errors import (CremeActiveSyncError, SYNC_ERR_WRONG_CFG_NO_SERVER_URL,
        SYNC_ERR_WRONG_CFG_NO_LOGIN, SYNC_ERR_WRONG_CFG_NO_PWD,
        SYNC_ERR_ABORTED, SYNC_ERR_WRONG_CFG_INVALID_SERVER_URL)
from .mappings import FOLDERS_TYPES_CREME_TYPES_MAPPING, CREME_AS_MAPPING
from .messages import MessageInfo, MessageSucceed, MessageError, _INFO, _ERROR, _SUCCESS
from .models import CremeClient, AS_Folder
from .utils import is_user_sync_calendars, is_user_sync_contacts, get_default_server_setting_values


INFO    = 'info'
ERROR   = 'error'
SUCCESS = 'success'

url_validator = validators.URLValidator()

# ACTIVE_SYNC_DEBUG = settings.ACTIVE_SYNC_DEBUG


class Synchronization(object):
    """
        TODO: Handle SSL & Domain
    """
    def __init__(self, user, *args, **kwargs):
        self.user = user
        self.client = CremeClient.objects.get_or_create(user=user)[0]
        self.client_id  = self.client.client_id
        self.policy_key = self.client.policy_key
        self.last_sync  = self.client.last_sync
        self.contact_folder_id = self.client.contact_folder_id
        self.sync_key = self.client.sync_key
        self.folder_sync_key = self.client.folder_sync_key
        self._data = {
            'debug': {
                'xml': [],
                'errors': [],
                'info': [],
            },
        }
        self.is_user_sync_calendars = is_user_sync_calendars(user)
        self.is_user_sync_contacts  = is_user_sync_contacts(user)

        # TODO: If messages will be used somewhere else activate the django messaging system
        self._messages = defaultdict(list)

        # sv_get = SettingValue.objects.get
        # sv_doesnotexist = SettingValue.DoesNotExist
        user_settings = user.settings
        _default_values = {}

        # TODO: factorise (see blocks.py)
        def get_default_value(key):
            if not _default_values:
                _default_values.update(get_default_server_setting_values())

            return _default_values[key]

        # try:
        #     self.server_url = sv_get(key_id=USER_MOBILE_SYNC_SERVER_URL, user=user).value
        # except sv_doesnotexist:
        #     try:
        #         self.server_url = sv_get(key_id=MAPI_SERVER_URL).value
        #     except sv_doesnotexist:
        #         raise CremeActiveSyncError(SYNC_ERR_WRONG_CFG_NO_SERVER_URL)
        try:
            self.server_url = user_settings[setting_keys.user_msync_server_url_key]
        except KeyError:
            self.server_url = get_default_value('url').value

        if not self.server_url.strip():
            raise CremeActiveSyncError(SYNC_ERR_WRONG_CFG_NO_SERVER_URL)

        try:
            url_validator(self.server_url)
        except ValidationError:
            raise CremeActiveSyncError(SYNC_ERR_WRONG_CFG_INVALID_SERVER_URL)

        # try:
        #     self.domain = sv_get(key_id=USER_MOBILE_SYNC_SERVER_DOMAIN, user=user).value
        # except sv_doesnotexist:
        #     try:
        #         self.domain = sv_get(key_id=MAPI_DOMAIN).value
        #     except sv_doesnotexist:
        #         self.domain = None
        try:
            self.domain = user_settings[setting_keys.user_msync_server_domain_key]
        except KeyError:
            self.domain = get_default_value('domain').value

        # try:
        #     self.server_ssl = sv_get(key_id=USER_MOBILE_SYNC_SERVER_SSL, user=user).value
        # except sv_doesnotexist:
        #     try:
        #         self.server_ssl = sv_get(key_id=MAPI_SERVER_SSL).value
        #     except sv_doesnotexist:
        #         self.server_ssl = False
        try:
            self.server_ssl = user_settings[setting_keys.user_msync_server_ssl_key]
        except KeyError:
            self.server_ssl = get_default_value('ssl').value

        # try:
        #     self.login = sv_get(key_id=USER_MOBILE_SYNC_SERVER_LOGIN, user=user).value
        #     if not self.login.strip():
        #         raise sv_doesnotexist
        # except sv_doesnotexist:
        #     raise CremeActiveSyncError(SYNC_ERR_WRONG_CFG_NO_LOGIN)
        self.login = login = user_settings.get(setting_keys.user_msync_server_login_key, '').strip()
        if not login:
            raise CremeActiveSyncError(SYNC_ERR_WRONG_CFG_NO_LOGIN)

        # try:
        #     self.pwd = Cipher.decrypt_from_db(sv_get(key_id=USER_MOBILE_SYNC_SERVER_PWD, user=user).value)
        #     if self.pwd.strip() == u'':
        #         raise sv_doesnotexist
        # except sv_doesnotexist:
        #     raise CremeActiveSyncError(SYNC_ERR_WRONG_CFG_NO_PWD)
        self.pwd = pwd = Cipher.decrypt_from_db(user_settings.get(setting_keys.user_msync_server_pwd_key, '')).strip()
        if not pwd:
            raise CremeActiveSyncError(SYNC_ERR_WRONG_CFG_NO_PWD)

        self.params = (self.server_url, self.login, self.pwd, self.client_id, self.user)

    # UI helpers -------------
    def add_message(self, level, msg):
        self._messages[msg.type].append(msg)

    def add_info_message(self, msg, **kwargs):
        self._messages[_INFO].append(MessageInfo(message=msg, **kwargs))

    def add_success_message(self, msg, **kwargs):
        self._messages[_SUCCESS].append(MessageSucceed(message=msg, **kwargs))

    def add_error_message(self, msg, **kwargs):
        self._messages[_ERROR].append(MessageError(message=msg, **kwargs))

    def messages(self):
        return self._messages.iteritems()

    def get_messages(self, level):
        return self._messages[level]

    def get_info_messages(self):
        return self._messages[INFO]

    def get_success_messages(self):
        return self._messages[SUCCESS]

    def get_error_messages(self):
        return self._messages[ERROR]

    def merge_command_messages(self, cmd):
        for type, messages in cmd.messages():
            self._messages[type].extend(messages)
    # UI helpers [end] -------------

    def synchronize(self):
        """Complete synchronization process"""
        policy_key = self.policy_key
        folder_sync_key = self.folder_sync_key or 0
        sync_key = self.sync_key or 0
        folders = []
        folders_append = folders.append
        client = self.client

        self._data['debug']['info'].append("Begin with policy_key: %s" % policy_key)

        _fs = self._folder_sync(policy_key, folder_sync_key)  # Try to sync server folders
        fs  = self._handle_folder_sync(_fs)

        as_folder_get_or_create = AS_Folder.objects.get_or_create
        for added_folder in fs.add:
            folder = as_folder_get_or_create(client=client,
                                             server_id=added_folder.get('serverid'),
                                             type=added_folder.get('type'),
                                            )[0]

            folder.parent_id=added_folder.get('parentid')
            folder.display_name=added_folder.get('displayname')

            creme_model = FOLDERS_TYPES_CREME_TYPES_MAPPING.get(folder.type)
            creme_model_AS_values = CREME_AS_MAPPING.get(creme_model)
            if creme_model_AS_values is not None:
                folder.as_class = creme_model_AS_values['class']

            folder.save()
            folders_append(folder)

        client.folder_sync_key = fs.synckey

        if not folders:
            folders = AS_Folder.objects.filter(client=client)

        # Synchronizing entities
        as_ = self._sync(policy_key, folders, sync_key, True)
        if hasattr(as_, 'last_synckey'):
            # If none of folders is synchronized (which can happen if the user has chosen "to sync nothing"...)
            client.sync_key = as_.last_synckey

        self._data['debug']['info'].append("client.sync_key : %s" % client.sync_key)

#        #We delete the mapping for deleted entities
#        # TODO: Verify the status ?
#        CremeExchangeMapping.objects.filter(was_deleted=True, user=user).delete()

        # TODO: Try except and put this in the else
        client.policy_key = policy_key
        client.last_sync  = now()
        client.save()

    def _sync(self, policy_key, as_folder, synckey=None, fetch=True):
        as_ = AirSync(*self.params)
        as_.send(policy_key, as_folder, synckey, fetch)

        self.merge_command_messages(as_)

        # if ACTIVE_SYNC_DEBUG:
        if settings.ACTIVE_SYNC_DEBUG:
            self._data['debug']['xml'].extend(as_._data['debug']['xml'])

        return as_

    def _folder_sync(self, policy_key, sync_key=0):
        """Process a foldersync command
        @returns : A FolderSync instance
        """
        fs = FolderSync(*self.params)

        try:
            fs.send(policy_key, sync_key)
        except CremeActiveSyncError:
            self._data['debug']['errors'].extend(fs._data['debug']['errors'])
            raise

        self.merge_command_messages(fs)

        # if ACTIVE_SYNC_DEBUG:
        if settings.ACTIVE_SYNC_DEBUG:
            self._data['debug']['xml'].extend(fs._data['debug']['xml'])

        return fs

    def _handle_folder_sync(self, folder_sync):
        if folder_sync.status == as_constants.SYNC_FOLDER_STATUS_SUCCESS:
            return folder_sync

        if folder_sync.status == as_constants.SYNC_NEED_CURRENT_POLICY:
            self._data['debug']['info'].append("SYNC_NEED_CURRENT_POLICY")
            # Permission denied we need a new policy_key
            provision = Provision(*self.params)
            provision.send()
            policy_key = provision.policy_key

            # if ACTIVE_SYNC_DEBUG:
            if settings.ACTIVE_SYNC_DEBUG:
                self._data['debug']['xml'].extend(provision._data['debug']['xml'])

            self._data['debug']['info'].append("policy_key : %s" % policy_key)

            # Trying again to sync folders
            _fs = self._folder_sync(policy_key, folder_sync.sync_key)
            fs  = self._handle_folder_sync(_fs)

            self._data['debug']['info'].append("policy_key : %s" % policy_key)
            return fs

        if folder_sync.status == as_constants.SYNC_FOLDER_STATUS_INVALID_SYNCKEY:
            _fs = self._folder_sync(0, 0)
            fs  = self._handle_folder_sync(_fs)
            return fs

        if folder_sync.status in (as_constants.SYNC_FOLDER_STATUS_SERVER_ERROR,
                                  as_constants.SYNC_FOLDER_STATUS_TIMEOUT,
                                  as_constants.SYNC_FOLDER_STATUS_BAD_REQUEST,
                                  as_constants.SYNC_FOLDER_STATUS_UNKNOW_ERROR,
                                  as_constants.SYNC_FOLDER_STATUS_ERROR):
            self.add_error_message(_(u'There is a server error, please try again later…'))
            raise CremeActiveSyncError(SYNC_ERR_ABORTED)
