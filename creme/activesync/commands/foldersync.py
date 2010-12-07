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

from activesync import xml2util

from base import Base

class FolderSync(Base):

    template_name = "activesync/commands/xml/foldersync/request_min.xml"
    command       = "FolderSync"

    def __init__(self, *args, **kwargs):
        super(FolderSync, self).__init__(*args, **kwargs)
        self._create_connection()

    def send(self, policy_key):
        xml = super(FolderSync, self).send({'synckey': 0}, headers={"X-Ms-Policykey": policy_key})
        ns = "{FolderHierarchy:}"

        self.status  = xml.find('%sStatus' % ns).text
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
        

    def send_old(self, policy_key):
        xml = super(FolderSync, self).send({'synckey': 0}, headers={"X-Ms-Policykey": policy_key})
        xp = xml.xpathNewContext()
        xp.xpathRegisterNs("f", "FolderHierarchy:")

        self.synckey = None
        self.status = None

        get_node_value  = xml2util.GetNodeValue
        find_child_node = xml2util.FindChildNode

        for node in xp.xpathEval("/f:FolderSync"):
            self.synckey = get_node_value(find_child_node(node, "SyncKey"))
            self.status  = get_node_value(find_child_node(node, "Status"))

        self.add = []
        for node in xp.xpathEval("/f:FolderSync/f:Changes/f:Add"):

            self.add.append({
                'serverid'    : get_node_value(find_child_node(node, "ServerId")),
                'parentid'    : get_node_value(find_child_node(node, "ParentId")),
                'displayname' : get_node_value(find_child_node(node, "DisplayName")),
                'type'        : get_node_value(find_child_node(node, "Type")),
            })

#            self.count = get_node_value(find_child_node(node, "Count"))





        
