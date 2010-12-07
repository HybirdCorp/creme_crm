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
from activesync.constants import SYNC_PROVISION_RWSTATUS_NA

from base import Base

class Provision(Base):

    template_name = "activesync/commands/xml/provision/request_min.xml"
    command       = "Provision"

    def __init__(self, *args, **kwargs):
        super(Provision, self).__init__(*args, **kwargs)
        self._create_connection()

    def send(self):
        xml = super(Provision, self).send({'rw_status': SYNC_PROVISION_RWSTATUS_NA})

        ns = "{Provision:}"
        policy_node = xml.find('%sPolicies/%sPolicy' % (ns, ns))
        
        self.status     = policy_node.find('%sStatus' % ns).text
        self.policy_key = policy_node.find('%sPolicyKey' % ns).text

    def send_old(self):#libxml2 version
        xml = super(Provision, self).send({'rw_status': SYNC_PROVISION_RWSTATUS_NA})
        xp = xml.xpathNewContext()
        xp.xpathRegisterNs("p", "Provision:")

        self.status     = None
        self.policy_key = None

        get_node_value  = xml2util.GetNodeValue
        find_child_node = xml2util.FindChildNode
        for node in xp.xpathEval("/p:Provision/p:Policies/p:Policy"):
            self.status     = get_node_value(find_child_node(node, "Status"))
            self.policy_key = get_node_value(find_child_node(node, "PolicyKey"))
#            policy_type = xml2util.GetNodeValue(xml2util.FindChildNode(node, "PolicyType"))
#            data        = xml2util.GetNodeValue(xml2util.FindChildNode(node, "Data"))
