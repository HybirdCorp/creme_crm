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
from itertools import imap
from xml.etree.ElementTree import tostring

from base import Base

from activesync.contacts import serialize_contact, CREME_CONTACT_MAPPING
from activesync.models.active_sync import CremeExchangeMapping

from persons.models.contact import Contact

class AirSync(Base):

    template_name = "activesync/commands/xml/airsync/request_min.xml"
    command       = "Sync"

    def __init__(self, *args, **kwargs):
        super(AirSync, self).__init__(*args, **kwargs)
        self._create_connection()

    def send(self, policy_key, server_id, synckey=None, fetch=True, user=None):
        """
            @param policy_key string set in the header to be authorized
            @param server_id
            @param synckey None to fetch all server changes or last synckey supplied by server
            @param fetch True for fetching changes False for current pushing changes
        """

        extra_ns = {'A1': 'Contacts:', 'A2': 'AirSyncBase:', 'A3': 'Contacts2:'}
        reverse_ns = dict((v,k) for k, v in extra_ns.iteritems())

        ns0 = "{AirSync:}"
        ns1 = "{Contacts:}"

        self.last_synckey = synckey

        if synckey is None:
            supported = []

            for prefix, ns in CREME_CONTACT_MAPPING.iteritems():
                for item in ns.values():
                    supported.append("<%s:%s/>" % (reverse_ns.get(prefix), item))#TODO: Remove : if no prefix

            xml = super(AirSync, self).send({'class': "Contacts", 'synckey': 0, 'server_id': server_id, 'supported': supported, 'extra_ns': extra_ns}, headers={"X-Ms-Policykey": policy_key})

            self.last_synckey = xml.find('%sCollections/%sCollection/%sSyncKey' % (ns0, ns0, ns0)).text
            status    = xml.find('%sCollections/%sCollection/%sStatus' % (ns0, ns0, ns0)).text
            server_id = xml.find('%sCollections/%sCollection/%sCollectionId' % (ns0, ns0, ns0)).text

        if fetch:
            xml2 = super(AirSync, self).send({'class': "Contacts", 'synckey': self.last_synckey, 'server_id': server_id, 'fetch': True, 'extra_ns': extra_ns}, headers={"X-Ms-Policykey": policy_key})

            add_nodes = xml2.findall('%(ns0)sCollections/%(ns0)sCollection/%(ns0)sCommands/%(ns0)sAdd' % {'ns0': ns0})

            self.last_synckey = xml2.find('%sCollections/%sCollection/%sSyncKey' % (ns0, ns0, ns0)).text

            for add_node in add_nodes:
                server_id_pk = add_node.find('%(ns0)sServerId' % {'ns0': ns0})#This is the object pk on the server map it whith cremepk
                app_data     = add_node.find('%(ns0)sApplicationData' % {'ns0': ns0})

                create = CremeExchangeMapping.objects.create

                data = {'user': user}
#                fn = app_data.find('%(ns1)sFirstName' % {'ns1': ns1}).text
#                ln = app_data.find('%(ns1)sLastName'  % {'ns1': ns1}).text
                for ns, field_dict in CREME_CONTACT_MAPPING.iteritems():
                    for c_field, x_field in field_dict.iteritems():
                        d = app_data.find('{%s}%s' % (ns, x_field))
                        if d is not None:
                            data[c_field] = d.text

                print "data :", data
#                c, is_created = Contact.objects.get_or_create(**data)
#                create(creme_entity_id=c.pk, exchange_entity_id=server_id_pk)


        add_objects = map(lambda c:  add_object(c, lambda cc: serialize_contact(cc, reverse_ns)), [Contact.objects.get(pk=16)])#TODO: Remove hard coded
        xml3 = super(AirSync, self).send({'class': "Contacts", 'synckey': self.last_synckey, 'server_id': server_id, 'fetch': False, 'objects': add_objects, 'extra_ns': extra_ns}, headers={"X-Ms-Policykey": policy_key})
        xml3_collection = xml3.find('%(ns0)sCollections/%(ns0)sCollection' % {'ns0': ns0})
        self.last_synckey = xml3_collection.find('%(ns0)sSynckey' % {'ns0': ns0})
        status = xml3_collection.find('%(ns0)sStatus' % {'ns0': ns0})
        responses = xml3_collection.find('%(ns0)sResponses' % {'ns0': ns0})

        self.synced = {
            "Add":[],
        }

        add_nodes = responses.findall('%(ns0)sAdd' % {'ns0': ns0})
        add_stack = self.synced['Add']
        for add_node in add_nodes:
            add_stack.append({
                'client_id' : add_node.find('%(ns0)sClientId' % {'ns0': ns0}).text, #Creme PK
                'server_id' : add_node.find('%(ns0)sServerId' % {'ns0': ns0}).text, #Server PK
                'status'    : add_node.find('%(ns0)sStatus'   % {'ns0': ns0}).text,
            })
            

def add_object(o, serializer):
    return "<Add><ClientId>%s</ClientId><ApplicationData>%s</ApplicationData></Add>" % (o.id, serializer(o))


#<ns0:Sync xmlns:ns0="AirSync:">
#    <ns0:Collections>
#        <ns0:Collection>
#        <ns0:Class>Contacts</ns0:Class>
#        <ns0:SyncKey>{c10d700e-2a23-41ef-b27a-c060dc781684}3</ns0:SyncKey>
#        <ns0:CollectionId>2e9ce20a99cc4bc39804d5ee956855311100000000000000</ns0:CollectionId>
#        <ns0:Status>1</ns0:Status>
#        <ns0:Responses>
#            <ns0:Add>
#                <ns0:ClientId>16</ns0:ClientId>
#                <ns0:ServerId>2e9ce20a99cc4bc39804d5ee956855319700000000000000</ns0:ServerId>
#                <ns0:Status>1</ns0:Status>
#            </ns0:Add>
#        </ns0:Responses></ns0:Collection></ns0:Collections></ns0:Sync>

#<Add>...</Add>
#<Delete>...</Delete>
#<Change>...</Change>
#<Fetch>...</Fetch>

#<Commands>
#    <Add>
#        <ClientId>123</ClientId>
#        <ApplicationData>
#            <contacts:Email1Address>schai@fourthcoffee.com</contacts:Email1Address>
#            <contacts:FirstName>Sean</contacts:FirstName>
#            <contacts:MiddleName>W</contacts:MiddleName>
#            <contacts:LastName>Chai</contacts:LastName>
#            <contacts:Title>Sr Marketing Manager</contacts:Title>
#        </ApplicationData>
#    </Add>
#</Commands


#<Change>
#    <ServerId>3:1</ServerId>
#    <ApplicationData>
#        <contacts:Email1Address>jsmith@fourthcoffee.com</contacts:Email1Address>
#        <contacts:FirstName>Jeff</contacts:FirstName>
#    </ApplicationData>
#</Change>









        
