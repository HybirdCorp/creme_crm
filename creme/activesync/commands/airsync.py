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

from django.contrib.auth.models import User
from activesync import xml2util

from xml.etree.ElementTree import tostring
from base import Base

from persons.models.contact import Contact

class AirSync(Base):

    template_name = "activesync/commands/xml/airsync/request_min.xml"
    command       = "Sync"

    def __init__(self, *args, **kwargs):
        super(AirSync, self).__init__(*args, **kwargs)
        self._create_connection()

    def send(self, policy_key, server_id, synckey):
        xml = super(AirSync, self).send({'class': "Contacts", 'synckey': 0, 'server_id': server_id}, headers={"X-Ms-Policykey": policy_key})
        ns0 = "{AirSync:}"
        ns1 = "{Contacts:}"

        new_synckey = xml.find('%sCollections/%sCollection/%sSyncKey' % (ns0, ns0, ns0)).text
        status      = xml.find('%sCollections/%sCollection/%sStatus' % (ns0, ns0, ns0)).text
        server_id   = xml.find('%sCollections/%sCollection/%sCollectionId' % (ns0, ns0, ns0)).text

        xml2 = super(AirSync, self).send({'class': "Contacts", 'synckey': new_synckey, 'server_id': server_id}, headers={"X-Ms-Policykey": policy_key})

        add_nodes = xml2.findall('%(ns0)sCollections/%(ns0)sCollection/%(ns0)sCommands/%(ns0)sAdd' % {'ns0': ns0})

        for add_node in add_nodes:
            app_data = add_node.find('%(ns0)sApplicationData' % {'ns0': ns0})

            fn = app_data.find('%(ns1)sFirstName' % {'ns1': ns1}).text
            ln = app_data.find('%(ns1)sLastName'  % {'ns1': ns1}).text

            Contact.objects.get_or_create(first_name=fn, last_name=ln, user=User.objects.get(pk=1))







        
