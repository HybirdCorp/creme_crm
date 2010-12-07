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

from itertools import imap
from xml.etree.ElementTree import tostring

from django.db.models import Q
from django.contrib.auth.models import User

from base import Base

from activesync.contacts import serialize_contact, CREME_CONTACT_MAPPING, save_contact
from activesync.models.active_sync import CremeExchangeMapping
from activesync import config

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
        print "AirSync policy_key:%s, server_id: %s, synckey=%s, fetch=%s, user=%s" % (policy_key, server_id, synckey, fetch, user)
        extra_ns = {'A1': 'Contacts:', 'A2': 'AirSyncBase:', 'A3': 'Contacts2:'}
        reverse_ns = dict((v,k) for k, v in extra_ns.iteritems())
        reverse_ns_get = reverse_ns.get

        ns0 = "{AirSync:}"
        ns1 = "{Contacts:}"
        d_ns0 = {'ns0': ns0}
        exch_map_manager = CremeExchangeMapping.objects
        self.last_synckey = synckey
        options = {
            'Conflict': config.CONFLICT_MODE,
        }

        if synckey is None:
            supported = []
            supported_append = supported.append

            for prefix, ns in CREME_CONTACT_MAPPING.iteritems():
                for item in ns.values():
                    ns_prefix = reverse_ns_get(prefix)
                    supported_append("<%s%s/>" % ('%s:' % ns_prefix if ns_prefix else '', item))

            xml = super(AirSync, self).send({'class': "Contacts", 'synckey': 0, 'server_id': server_id, 'supported': supported, 'extra_ns': extra_ns}, headers={"X-Ms-Policykey": policy_key})

            collection = xml.find('%(ns0)sCollections/%(ns0)sCollection' % d_ns0)
            collection_find   = collection.find
            
            self.last_synckey = collection_find('%(ns0)sSyncKey' % d_ns0).text
            status            = collection_find('%(ns0)sStatus' % d_ns0).text
            server_id         = collection_find('%(ns0)sCollectionId' % d_ns0).text

        if fetch:
            xml2 = super(AirSync, self).send({'class': "Contacts", 'synckey': self.last_synckey, 'server_id': server_id, 'fetch': True, 'extra_ns': extra_ns, 'options': options}, headers={"X-Ms-Policykey": policy_key})

            print "\n\n xml2 :", tostring(xml2), "\n\n"

            add_nodes = xml2.findall('%(ns0)sCollections/%(ns0)sCollection/%(ns0)sCommands/%(ns0)sAdd' % d_ns0)

            self.last_synckey = xml2.find('%(ns0)sCollections/%(ns0)sCollection/%(ns0)sSyncKey' % d_ns0).text
            
            create = exch_map_manager.create

            print "len(add_nodes) :", len(add_nodes)

            for add_node in add_nodes:
                add_node_find = add_node.find
                
                server_id_pk  = add_node_find('%(ns0)sServerId' % d_ns0).text#This is the object pk on the server map it whith cremepk
                app_data      = add_node_find('%(ns0)sApplicationData' % d_ns0)
                app_data_find = app_data.find

                data = {'user': user}
                for ns, field_dict in CREME_CONTACT_MAPPING.iteritems():
                    for c_field, x_field in field_dict.iteritems():
                        d = app_data_find('{%s}%s' % (ns, x_field))
                        if d is not None:
                            if callable(c_field):
                                c_field = c_field(needs_attr=True)

                            if c_field and c_field.strip() != '':
                                data[c_field] = d.text

                contact = save_contact(data, user)
                create(creme_entity_id=contact.id, exchange_entity_id=server_id_pk, synced=True)
                print "create :", contact

        q_not_synced = ~Q(pk__in=exch_map_manager.filter(synced=True).values_list('creme_entity_id', flat=True))

        add_objects = map(lambda c:  add_object(c, lambda cc: serialize_contact(cc, reverse_ns)), Contact.objects.filter(q_not_synced & Q(is_deleted=False)))
        xml3 = super(AirSync, self).send({'class': "Contacts", 'synckey': self.last_synckey, 'server_id': server_id, 'fetch': False, 'objects': add_objects, 'extra_ns': extra_ns}, headers={"X-Ms-Policykey": policy_key})
        xml3_collection = xml3.find('%(ns0)sCollections/%(ns0)sCollection' % d_ns0)
        xml3_collection_find = xml3_collection.find

        print "\n\n xml3 :", tostring(xml3), "\n\n"

        self.last_synckey = xml3_collection_find('%(ns0)sSynckey' % d_ns0)
        status            = xml3_collection_find('%(ns0)sStatus' % d_ns0)
        responses         = xml3_collection_find('%(ns0)sResponses' % d_ns0)

        self.synced = {
            "Add":[],
        }

        if responses is not None:
            add_nodes = responses.findall('%(ns0)sAdd' % d_ns0)
            add_stack = self.synced['Add']
            add_stack_append = add_stack.append
            for add_node in add_nodes:
                add_node_find = add_node.find
                add_stack_append({
                    'client_id' : add_node_find('%(ns0)sClientId' % d_ns0).text, #Creme PK
                    'server_id' : add_node_find('%(ns0)sServerId' % d_ns0).text, #Server PK
                    'status'    : add_node_find('%(ns0)sStatus'   % d_ns0).text,
                })

#            change_nodes = 
            

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

#Img >~ 200Ko
# xml3: <ns0:Sync xmlns:ns0="AirSync:">
#<ns0:Collections>
#    <ns0:Collection>
#        <ns0:Class>Contacts</ns0:Class>
#        <ns0:SyncKey>{6dcd97d8-b1f2-4ef6-80e1-c46f69fcdfc5}3</ns0:SyncKey>
#        <ns0:CollectionId>2e9ce20a99cc4bc39804d5ee956855311100000000000000</ns0:CollectionId>
#        <ns0:Status>1</ns0:Status>
#        <ns0:Responses>
#            <ns0:Add>
#                <ns0:ClientId>4</ns0:ClientId>
#                <ns0:ServerId>2e9ce20a99cc4bc39804d5ee956855318701000000000000</ns0:ServerId>
#                <ns0:Status>1</ns0:Status>
#            </ns0:Add>
#            <ns0:Add>
#                <ns0:ClientId>16</ns0:ClientId>
#                <ns0:ServerId>2e9ce20a99cc4bc39804d5ee956855318801000000000000</ns0:ServerId>
#                <ns0:Status>1</ns0:Status>
#            </ns0:Add>
#        </ns0:Responses>
#    </ns0:Collection>
#</ns0:Collections>
#</ns0:Sync>







        
