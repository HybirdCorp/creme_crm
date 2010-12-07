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

from creme_config.models.config_models import CremeKVConfig
from creme_config.constants import (MAPI_DOMAIN, MAPI_SERVER_SSL, MAPI_SERVER_URL,
                                    USER_MOBILE_SYNC_SERVER_DOMAIN,
                                    USER_MOBILE_SYNC_SERVER_LOGIN,
                                    USER_MOBILE_SYNC_SERVER_PWD,
                                    USER_MOBILE_SYNC_SERVER_SSL,
                                    USER_MOBILE_SYNC_SERVER_URL)

from activesync.models.active_sync import CremeClient, CremeExchangeMapping
from activesync.commands import FolderSync, Provision, AirSync
from activesync.constants import SYNC_FOLDER_TYPE_CONTACT, SYNC_NEED_CURRENT_POLICY

class WrongSyncConfig(Exception):
    pass

class Synchronization(object):
    """
        TODO: Handle SSL & Domain
    """
    def __init__(self, user, *args, **kwargs):
        self.user = user
        self.client = CremeClient.objects.get_or_create(user=user)[0]
        self.client_id  = self.client.client_id
        self.policy_key = self.client.policy_key
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
                raise WrongSyncConfig(_(u"No server url, please fill in information in global settings configuration or in your own settings"))

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
            raise WrongSyncConfig(_(u"No login, please fill in information in your own settings"))

        try:
            self.pwd = ckv_get(pk=USER_MOBILE_SYNC_SERVER_PWD % user_id).value
            if self.pwd.strip() == u"":
                raise ckv_doesnotexist
        except ckv_doesnotexist:
            raise WrongSyncConfig(_(u"No password, please fill in information in your own settings"))

        self.params = (self.server_url, self.login, self.pwd, self.client_id)

    def synchronize(self):
        params = self.params
        policy_key = self.policy_key
        sync_key   = self.sync_key or 0
        contacts   = []
        provisionned = False

        fs = self.folder_sync(policy_key, sync_key)#Try to sync server folders

        if fs.status == SYNC_NEED_CURRENT_POLICY:
            #Permission denied we need a new policy_key
            provisionned = True
            provision = Provision(*params)
            provision.send()
            policy_key = provision.policy_key

            #Trying again to sync folders
            fs = self.folder_sync(policy_key, sync_key)

        #For the moment we fetch only the contacts folder
        contacts = filter(lambda x: int(x['type']) == SYNC_FOLDER_TYPE_CONTACT, fs.add)

        if contacts:#The contact folder exists
            contact_folder = contacts[0]
            serverid       = contact_folder.get('serverid')#Contact folder id

            if provisionned:
                as_ = self.sync(policy_key, serverid, None, True, user=self.user)
            else:
                as_ = self.sync(policy_key, serverid, fs.synckey, True, user=self.user)

            self.client.sync_key = as_.last_synckey
            self.client.policy_key = policy_key

            create = CremeExchangeMapping.objects.create
            for synced in as_.synced['Add']:#Only add for the moment
                client_id = synced.get('client_id')
                server_id = synced.get('server_id')
                create(creme_entity_id=client_id, exchange_entity_id=server_id)#Create objects

        self.client.save()

    def sync(self, policy_key, serverid, synckey=None, fetch=True, user=None):
        as_ = AirSync(*self.params)
        as_.send(policy_key, serverid, synckey, fetch, user)
        return as_

    def folder_sync(self, policy_key, sync_key=0):
        fs = FolderSync(*self.params)
        fs.send(policy_key, sync_key)
        return fs
        
        
        
        
        