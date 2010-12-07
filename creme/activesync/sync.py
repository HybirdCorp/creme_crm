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
from datetime import datetime

from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from creme_config.models.config_models import CremeKVConfig
from creme_config.constants import (MAPI_DOMAIN, MAPI_SERVER_SSL, MAPI_SERVER_URL,
                                    USER_MOBILE_SYNC_SERVER_DOMAIN,
                                    USER_MOBILE_SYNC_SERVER_LOGIN,
                                    USER_MOBILE_SYNC_SERVER_PWD,
                                    USER_MOBILE_SYNC_SERVER_SSL,
                                    USER_MOBILE_SYNC_SERVER_URL)

from activesync.errors import (CremeActiveSyncError,
                               SYNC_ERR_WRONG_CFG_NO_SERVER_URL,
                               SYNC_ERR_WRONG_CFG_NO_LOGIN,
                               SYNC_ERR_WRONG_CFG_NO_PWD)
                               
from activesync.models.active_sync import CremeClient, CremeExchangeMapping
from activesync.commands import FolderSync, Provision, AirSync
from activesync.constants import SYNC_FOLDER_TYPE_CONTACT, SYNC_NEED_CURRENT_POLICY

class Synchronization(object):
    """
        TODO: Handle SSL & Domain
    """
    def __init__(self, user, *args, **kwargs):
        self.user = user
        self.client = CremeClient.objects.get_or_create(user=user)[0]
        self.client_id  = self.client.client_id
        self.policy_key = self.client.policy_key
        self.contact_folder_id = self.client.contact_folder_id
        self.sync_key = self.client.sync_key
        user_id = user.id
        
        ckv_get = CremeKVConfig.objects.get
        ckv_doesnotexist = CremeKVConfig.DoesNotExist

        try:
            self.server_url = ckv_get(pk=USER_MOBILE_SYNC_SERVER_URL % user_id).value
            if self.server_url.strip() == u"":
                raise ckv_doesnotexist
        except ckv_doesnotexist:
            try:
                self.server_url = ckv_get(pk=MAPI_SERVER_URL).value
            except ckv_doesnotexist:
                raise CremeActiveSyncError(SYNC_ERR_WRONG_CFG_NO_SERVER_URL)

        try:
            self.domain = ckv_get(pk=USER_MOBILE_SYNC_SERVER_DOMAIN % user_id).value
        except ckv_doesnotexist:
            try:
                self.domain = ckv_get(pk=MAPI_DOMAIN).value
            except ckv_doesnotexist:
                self.domain = None
            
        try:
            self.server_ssl = ckv_get(pk=USER_MOBILE_SYNC_SERVER_SSL % user_id).value
        except ckv_doesnotexist:
            try:
                self.server_ssl = ckv_get(pk=MAPI_SERVER_SSL).value
            except ckv_doesnotexist:
                self.server_ssl = False

        try:
            self.login = ckv_get(pk=USER_MOBILE_SYNC_SERVER_LOGIN % user_id).value
            if self.login.strip() == u"":
                raise ckv_doesnotexist
        except ckv_doesnotexist:
            raise CremeActiveSyncError(SYNC_ERR_WRONG_CFG_NO_LOGIN)
        
        try:
            self.pwd = ckv_get(pk=USER_MOBILE_SYNC_SERVER_PWD % user_id).value
            if self.pwd.strip() == u"":
                raise ckv_doesnotexist
        except ckv_doesnotexist:
            raise CremeActiveSyncError(SYNC_ERR_WRONG_CFG_NO_PWD)

        self.params = (self.server_url, self.login, self.pwd, self.client_id)

    def synchronize(self):
        """Complete synchronization process"""
        params = self.params
        policy_key = self.policy_key
        sync_key   = self.sync_key or 0
        contacts   = []
        client     = self.client
        user       = self.user
        provisionned = False
        
        fs = self._folder_sync(policy_key, sync_key)#Try to sync server folders
        
        if fs.status == SYNC_NEED_CURRENT_POLICY:
            #Permission denied we need a new policy_key
            provisionned = True
            provision = Provision(*params)
            provision.send()
            policy_key = provision.policy_key

            #Trying again to sync folders
            fs = self._folder_sync(policy_key, sync_key)

        #For the moment we fetch only the contacts folder
        contacts = filter(lambda x: int(x['type']) == SYNC_FOLDER_TYPE_CONTACT, fs.add)

        client.sync_key = fs.synckey
        
        if contacts:#The contact folder exists
            contact_folder = contacts[0]
            serverid       = contact_folder.get('serverid')#Contact folder id

        if self.contact_folder_id:
            serverid = self.contact_folder_id

        if serverid:
            client.contact_folder_id = serverid
            print "----CONTACT FOLDER :", serverid

            if provisionned:
                as_ = self._sync(policy_key, serverid, None, True, user=user)
            else:
                as_ = self._sync(policy_key, serverid, fs.synckey, True, user=user)

            client.sync_key = as_.last_synckey

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


        client.policy_key = policy_key
        client.last_sync  = datetime.now()
        client.save()

    def _sync(self, policy_key, serverid, synckey=None, fetch=True, user=None):
        as_ = AirSync(*self.params)
        as_.send(policy_key, serverid, synckey, fetch, user)
        return as_

    def _folder_sync(self, policy_key, sync_key=0):
        fs = FolderSync(*self.params)
        fs.send(policy_key, sync_key)
        return fs
        
        
        
        
        