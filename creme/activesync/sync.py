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
from collections import defaultdict
from datetime import datetime

from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from django.core import validators
from django.conf import settings

from creme_config.models.setting import SettingValue

from activesync.constants import (MAPI_DOMAIN, MAPI_SERVER_SSL, MAPI_SERVER_URL,
                                    USER_MOBILE_SYNC_SERVER_DOMAIN,
                                    USER_MOBILE_SYNC_SERVER_LOGIN,
                                    USER_MOBILE_SYNC_SERVER_PWD,
                                    USER_MOBILE_SYNC_SERVER_SSL,
                                    USER_MOBILE_SYNC_SERVER_URL)#TODO: * ?

from activesync.errors import (CremeActiveSyncError,
                               SYNC_ERR_WRONG_CFG_NO_SERVER_URL,
                               SYNC_ERR_WRONG_CFG_NO_LOGIN,
                               SYNC_ERR_WRONG_CFG_NO_PWD,
                               SYNC_ERR_ABORTED,
                               SYNC_ERR_WRONG_CFG_INVALID_SERVER_URL)#TODO: * ?
from activesync.messages import MessageInfo, MessageSucceed, MessageError, _INFO, _ERROR, _SUCCESS

                               
from activesync.models.active_sync import CremeClient, CremeExchangeMapping
from activesync.commands import FolderSync, Provision, AirSync
from activesync import constants as as_constants

INFO    = 'info'
ERROR   = 'error'
SUCCESS = 'success'

url_validator = validators.URLValidator()

ACTIVE_SYNC_DEBUG = settings.ACTIVE_SYNC_DEBUG

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
        self._data    = {
            'debug': {
                'xml': [],
                'errors': [],
                'info': [],
            },
        }

        #TODO: If messages will be used somewhere else activate the django messaging system
        self._messages = defaultdict(list)
                        
        sv_get = SettingValue.objects.get
        sv_doesnotexist = SettingValue.DoesNotExist

        try:
            self.server_url = sv_get(key__id=USER_MOBILE_SYNC_SERVER_URL, user=user).value
        except sv_doesnotexist:
            try:
                self.server_url = sv_get(key__id=MAPI_SERVER_URL).value
            except sv_doesnotexist:
                raise CremeActiveSyncError(SYNC_ERR_WRONG_CFG_NO_SERVER_URL)


        if self.server_url.strip() == u"":
            raise CremeActiveSyncError(SYNC_ERR_WRONG_CFG_NO_SERVER_URL)

        try:
            url_validator(self.server_url)
        except ValidationError:
            raise CremeActiveSyncError(SYNC_ERR_WRONG_CFG_INVALID_SERVER_URL)


        try:
            self.domain = sv_get(key__id=USER_MOBILE_SYNC_SERVER_DOMAIN, user=user).value
        except sv_doesnotexist:
            try:
                self.domain = sv_get(key__id=MAPI_DOMAIN).value
            except sv_doesnotexist:
                self.domain = None
            
        try:
            self.server_ssl = sv_get(key__id=USER_MOBILE_SYNC_SERVER_SSL, user=user).value
        except sv_doesnotexist:
            try:
                self.server_ssl = sv_get(key__id=MAPI_SERVER_SSL).value
            except sv_doesnotexist:
                self.server_ssl = False

        try:
            self.login = sv_get(key__id=USER_MOBILE_SYNC_SERVER_LOGIN, user=user).value
            if self.login.strip() == u"":
                raise sv_doesnotexist
        except sv_doesnotexist:
            raise CremeActiveSyncError(SYNC_ERR_WRONG_CFG_NO_LOGIN)
        
        try:
            self.pwd = sv_get(key__id=USER_MOBILE_SYNC_SERVER_PWD, user=user).value
            if self.pwd.strip() == u"":
                raise sv_doesnotexist
        except sv_doesnotexist:
            raise CremeActiveSyncError(SYNC_ERR_WRONG_CFG_NO_PWD)

        self.params = (self.server_url, self.login, self.pwd, self.client_id, self.user)


    ###### UI helpers #######
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
    ###### End UI helpers #######


    def synchronize(self):
        """Complete synchronization process"""
        params     = self.params
        policy_key = self.policy_key
        folder_sync_key = self.folder_sync_key or 0
        sync_key   = self.sync_key or 0
        contacts   = []
        client     = self.client
        user       = self.user

        self._data['debug']['info'].append("Begin with policy_key :%s" % policy_key)

        _fs = self._folder_sync(policy_key, folder_sync_key)#Try to sync server folders
        fs  = self._handle_folder_sync(_fs)

        #For the moment we fetch only the contacts folder
        contacts = filter(lambda x: int(x['type']) == as_constants.SYNC_FOLDER_TYPE_CONTACT, fs.add)

#        client.sync_key = fs.synckey
        client.folder_sync_key = fs.synckey
        
        if contacts:#The contact folder exists
            contact_folder = contacts[0]
            serverid       = contact_folder.get('serverid')#Contact folder id

        if self.contact_folder_id:
            serverid = self.contact_folder_id

        if serverid:
            client.contact_folder_id = serverid
            self._data['debug']['info'].append("CONTACT FOLDER : %s" % serverid)

#            if provisionned:
#                as_ = self._sync(policy_key, serverid, None, True, user=user)
#            else:
#            as_ = self._sync(policy_key, serverid, fs.synckey, True, user=user)
#            as_ = self._sync(policy_key, serverid, None, True, user=user)
            as_ = self._sync(policy_key, serverid, sync_key, True)

            client.sync_key = as_.last_synckey
            self._data['debug']['info'].append("client.sync_key : %s" % client.sync_key)

            c_x_mapping_manager = CremeExchangeMapping.objects
            create = c_x_mapping_manager.create
            as_synced = as_.synced
            for added in as_synced['Add']:
                client_id = added.get('client_id')
                server_id = added.get('server_id')
                create(creme_entity_id=client_id, exchange_entity_id=server_id, synced=True, user=user)#Create objects


            unchanged_server_id = [change.get('server_id') for change in as_synced['Change']]

            #Updating mapping only for entities actually changed on the server
            #Ensure we actually update for the right(current) user
            #TODO: Yet, we "just" send again next sync time so needed to handle status and act accordingly
            c_x_mapping_manager.filter(Q(is_creme_modified=True, user=user) & ~Q(exchange_entity_id__in=unchanged_server_id)).update(is_creme_modified=False)

            #We delete the mapping for deleted entities
            #TODO: Verify the status ?
            c_x_mapping_manager.filter(was_deleted=True, user=user).delete()

        #TODO: Try except and put this in the else
        client.policy_key = policy_key
        client.last_sync  = datetime.now()
        client.save()

    def _sync(self, policy_key, serverid, synckey=None, fetch=True):
        as_ = AirSync(*self.params)
        as_.send(policy_key, serverid, synckey, fetch)

        self.merge_command_messages(as_)

        if ACTIVE_SYNC_DEBUG:
            self._data['debug']['xml'].extend(as_._data['debug']['xml'])
            
        return as_

    def _folder_sync(self, policy_key, sync_key=0):
        """Process a foldersync command
           @returns : A FolderSync instance"""
        fs = FolderSync(*self.params)
        fs.send(policy_key, sync_key)

        self.merge_command_messages(fs)

        if ACTIVE_SYNC_DEBUG:
            self._data['debug']['xml'].extend(fs._data['debug']['xml'])

        return fs

    def _handle_folder_sync(self, folder_sync):

        if folder_sync.status == as_constants.SYNC_FOLDER_STATUS_SUCCESS:
            return folder_sync

        if folder_sync.status == as_constants.SYNC_NEED_CURRENT_POLICY:
            self._data['debug']['info'].append("SYNC_NEED_CURRENT_POLICY")
            #Permission denied we need a new policy_key
#            provisionned = True
            provision = Provision(*self.params)
            provision.send()
            policy_key = provision.policy_key

            if ACTIVE_SYNC_DEBUG:
                self._data['debug']['xml'].extend(provision._data['debug']['xml'])

            self._data['debug']['info'].append("policy_key : %s" % policy_key)

            #Trying again to sync folders
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

            self.add_error_message(_(u'There is a server error, please try again later...'))
            raise CremeActiveSyncError(SYNC_ERR_ABORTED)

        
        
        