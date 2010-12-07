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

import restkit.errors

from activesync.constants import SYNC_NEED_CURRENT_POLICY

from base import Base

class FolderSync(Base):

    template_name = "activesync/commands/xml/foldersync/request_min.xml"
    command       = "FolderSync"

    def __init__(self, *args, **kwargs):
        super(FolderSync, self).__init__(*args, **kwargs)
        self._create_connection()

    def send(self, policy_key, sync_key=0):
        xml = None
        try:
            xml = super(FolderSync, self).send({'synckey': sync_key}, headers={"X-Ms-Policykey": policy_key})
        except restkit.errors.RequestFailed, r:
            print "Error:" ,r.response.status
            if r.status_int == 449:
                self.status = SYNC_NEED_CURRENT_POLICY

        if xml is not None:
            ns = "{FolderHierarchy:}"

            self.status  = xml.find('%sStatus' % ns).text
            if self.status != SYNC_NEED_CURRENT_POLICY:
                self.synckey = xml.find('%sSyncKey' % ns).text

                self.add = []
                add_append = self.add.append
                add_nodes = xml.findall('%sChanges/%sAdd' % (ns,ns))

                for add_node in add_nodes:
                    add_append({
                        'serverid'    : add_node.find("%sServerId" % ns).text,
                        'parentid'    : add_node.find("%sParentId" % ns).text,
                        'displayname' : add_node.find("%sDisplayName" % ns).text,
                        'type'        : add_node.find("%sType" % ns).text,
                    })
        





        
