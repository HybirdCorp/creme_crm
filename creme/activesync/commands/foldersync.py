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

import restkit.errors

from ..constants import (SYNC_NEED_CURRENT_POLICY, SYNC_FOLDER_STATUS_ERROR,
        SYNC_FOLDER_STATUS_SUCCESS) #SYNC_FOLDER_STATUS_INVALID_SYNCKEY

from .base import Base


class FolderSync(Base):
    template_name = "activesync/commands/xml/foldersync/request_min.xml"
    command       = "FolderSync"

    def __init__(self, *args, **kwargs):
        super(FolderSync, self).__init__(*args, **kwargs)
        self._create_connection()

    def send(self, policy_key, sync_key=0, headers=None):
        xml = None
        self.synckey = sync_key
        self.status  = -1

        http_headers = {"X-Ms-Policykey": policy_key}

        if headers:
            http_headers.update(headers)

        try:
            xml = super(FolderSync, self).send({'synckey': sync_key}, headers=http_headers)
        except restkit.errors.RequestFailed, r:
            if r.status_int == 449:
                self.status = SYNC_NEED_CURRENT_POLICY
            elif r.status_int >= 400 and r.status_int < 500:
                #Could happend when AS version is not supported by the server
                self.status = SYNC_FOLDER_STATUS_ERROR


        if xml is not None:
            ns = "{FolderHierarchy:}"

            self.status  = xml.find('%sStatus' % ns).text

            try:
                self.status = int(self.status)
            except ValueError:
                self.status = SYNC_FOLDER_STATUS_ERROR

#            if self.status != SYNC_NEED_CURRENT_POLICY:
            if self.status == SYNC_FOLDER_STATUS_SUCCESS:
                print "[FolderSync] Doesn't need SYNC_NEED_CURRENT_POLICY"

                self.synckey = xml.find('%sSyncKey' % ns).text

                print "[FolderSync] self.synckey :", self.synckey

                self.add = []
                add_append = self.add.append
                add_nodes = xml.findall('%sChanges/%sAdd' % (ns,ns))#Todo: Handle: Changes / Delete ?

                for add_node in add_nodes:
                    try:
                        add_append({
                            'serverid'    : add_node.find("%sServerId" % ns).text,
                            'parentid'    : add_node.find("%sParentId" % ns).text,
                            'displayname' : add_node.find("%sDisplayName" % ns).text,
                            'type'        : int(add_node.find("%sType" % ns).text),
                        })
                    except (ValueError, TypeError):
                        continue

        print "[FolderSync] (end) Status :", self.status
#        self.add_info_message("[FolderSync] (end) Status : %s" % self.status)
