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

from django.conf import settings

from ..constants import SYNC_PROVISION_STATUS_SUCCESS # SYNC_PROVISION_RWSTATUS_NA SYNC_PROVISION_RWSTATUS_WIPED
from .base import Base


class Provision(Base):
    template_name = "activesync/commands/xml/provision/request_min.xml"
    command       = "Provision"
    ns            = "{Provision:}"

    def __init__(self, *args, **kwargs):
        super(Provision, self).__init__(*args, **kwargs)
        self._create_connection()

    def send(self, policy_key=0, remote_wipe=False):
        ns = self.ns
        policy_type = 'MS-EAS-Provisioning-WBXML'

        #Seems to be policy_type = 'MS-EAS-Provisioning-WBXML' for AS version >=12.0
        #and 'MS-WAP-Provisioning-XML' for AS version = 2.5

        if remote_wipe:
            xml = super(Provision, self).send({'rw_status': 1}, headers={"X-Ms-Policykey": policy_key})#TODO:Make constant with the 1
            self.policy_key = self.get_policy_key(xml)
            return

        include_settings = True
        if settings.IS_ZPUSH:
            include_settings = False
            policy_type = 'MS-WAP-Provisioning-XML'

        if policy_key == 0:
            xml = super(Provision, self).send({'settings': include_settings, 'policy_type': policy_type}, headers={"X-Ms-Policykey": policy_key})
            self.policy_key = self.get_policy_key(xml)
            policy_key= self.policy_key
            include_settings = False

        xml = super(Provision, self).send({'settings': include_settings, 'policy_type': policy_type, 'policy_key': policy_key, 'policy_status': 1}, headers={"X-Ms-Policykey": policy_key})#TODO:Make constant with the 1
#        xml = super(Provision, self).send({'rw_status': SYNC_PROVISION_RWSTATUS_NA}, headers={"X-Ms-Policykey": policy_key})

        direct_status = xml.find('%(ns)sStatus' % {'ns': ns})
        if direct_status is not None and direct_status.text != SYNC_PROVISION_STATUS_SUCCESS:
            return #TODO


        self.policy_key = self.get_policy_key(xml)
        self.status = self.get_status(xml)

    def get_policy_key(self, xml):
        ns = self.ns
        policy_node = xml.find('%(ns)sPolicies/%(ns)sPolicy' % {'ns': ns})

        policy_key = policy_node.find('%sPolicyKey' % ns)
        if policy_key is not None:
            policy_key = policy_key.text

        return policy_key

    def get_status(self, xml):
        ns = self.ns
        policy_node = xml.find('%(ns)sPolicies/%(ns)sPolicy' % {'ns': ns})
        status = policy_node.find('%sStatus' % ns)

        if status is not None:
            status = status.text

        return status
