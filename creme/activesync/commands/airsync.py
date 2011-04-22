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

from itertools import chain
from logging import debug, error
from xml.etree.ElementTree import tostring

from django.db.models import Q
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.db.utils import IntegrityError
from activesync.messages import MessageSucceedContactAdd, MessageSucceedContactUpdate, MessageInfoContactAdd

from base import Base

from activesync.contacts import (serialize_contact, CREME_CONTACT_MAPPING,
                                 save_contact, update_contact)

from activesync.models import (CremeExchangeMapping, CremeClient, SyncKeyHistory)
from activesync.constants import CONFLICT_SERVER_MASTER, SYNC_AIRSYNC_STATUS_SUCCESS, SYNC_AIRSYNC_STATUS_INVALID_SYNCKEY
from activesync.errors import (SYNC_ERR_VERBOSE, SYNC_ERR_CREME_PERMISSION_DENIED_CREATE,
                               SYNC_ERR_CREME_PERMISSION_DENIED_CHANGE_SPECIFIC, SYNC_ERR_CREME_PERMISSION_DENIED_DELETE_SPECIFIC)
from creme_core.models.entity import CremeEntity

from persons.models.contact import Contact

class AirSync(Base):

    template_name = "activesync/commands/xml/airsync/request_min.xml"
    command       = "Sync"

    def __init__(self, *args, **kwargs):
        super(AirSync, self).__init__(*args, **kwargs)
        self._create_connection()

    def send(self, policy_key, as_folder, synckey=None, fetch=True):
        """
            @param policy_key string set in the header to be authorized
            @param server_id
            @param synckey None to fetch all server changes or last synckey supplied by server
            @param fetch True for fetching changes False for current pushing changes
        """
        user = self.user
        server_id = as_folder.server_id
        
        print "AirSync policy_key:%s, server_id: %s, synckey=%s, fetch=%s, user=%s" % (policy_key, server_id, synckey, fetch, user)
        extra_ns = {'A1': 'Contacts:', 'A2': 'AirSyncBase:', 'A3': 'Contacts2:'}
        reverse_ns = dict((v,k) for k, v in extra_ns.iteritems())
        reverse_ns_get = reverse_ns.get

        ns0 = "{AirSync:}"
        ns1 = "{Contacts:}"
        d_ns = {'ns0': ns0, 'ns1': ns1}
        exch_map_manager = CremeExchangeMapping.objects
        exch_map_manager_get = exch_map_manager.get
        contact_getter = Contact.objects.get
        self.last_synckey = synckey
        CONFLICT_MODE = settings.CONFLICT_MODE
        IS_SERVER_MASTER = True if CONFLICT_MODE==CONFLICT_SERVER_MASTER else False

        client = CremeClient.objects.get(user=user)

        options = {
            'Conflict': CONFLICT_MODE,
        }

        self.synced = {
                        "Add":[],
                        "Change": [],
                      }

        if synckey in (0, 1, None):
            supported = []
            supported_append = supported.append

            for prefix, ns in CREME_CONTACT_MAPPING.iteritems():
                for item in ns.values():
                    ns_prefix = reverse_ns_get(prefix)
                    supported_append("<%s%s/>" % ('%s:' % ns_prefix if ns_prefix else '', item))

            xml = super(AirSync, self).send({'class': "Contacts", 'synckey': 0, 'server_id': server_id, 'supported': supported, 'extra_ns': extra_ns}, headers={"X-Ms-Policykey": policy_key})

            err_status_xml = xml.find('%(ns0)sStatus' % d_ns)
            if err_status_xml:
                #If the status is at the root it seems there is an error
                self.add_error_message(_(u"There was an error during synchronization phase. Error code : %s") % err_status_xml.text)
                return

            collection = xml.find('%(ns0)sCollections/%(ns0)sCollection' % d_ns)
            collection_find = collection.find
            
            self.last_synckey = collection_find('%(ns0)sSyncKey' % d_ns).text
            self.status       = collection_find('%(ns0)sStatus' % d_ns).text
            server_id         = collection_find('%(ns0)sCollectionId' % d_ns).text

            SyncKeyHistory.objects.create(client=client, sync_key=self.last_synckey)

            try:
                self.status = int(self.status)
            except ValueError:
                pass ###TODO: ???


            if self.status != SYNC_AIRSYNC_STATUS_SUCCESS:
                self.add_error_message(_(u"There was an error during synchronization phase. Try again later."))
                return

        if fetch:
            ################
            ##SERVER PART ##
            ################
            xml2 = super(AirSync, self).send({'class': "Contacts", 'synckey': self.last_synckey, 'server_id': server_id, 'fetch': True, 'extra_ns': extra_ns, 'options': options}, headers={"X-Ms-Policykey": policy_key})

#            print "\n\n xml2 :", tostring(xml2), "\n\n"

            xml2_collection      = xml2.find('%(ns0)sCollections/%(ns0)sCollection' % d_ns)
            xml2_collection_find = xml2_collection.find

#            self.last_synckey = xml2.find('%(ns0)sCollections/%(ns0)sCollection/%(ns0)sSyncKey' % d_ns).text
#            self.status       = xml2.find('%(ns0)sCollections/%(ns0)sCollection/%(ns0)sStatus' % d_ns).text

            self.last_synckey = xml2_collection_find('%(ns0)sSyncKey' % d_ns).text
            self.status       = xml2_collection_find('%(ns0)sStatus' % d_ns).text

            SyncKeyHistory.objects.create(client=client, sync_key=self.last_synckey)

            try:
                self.status = int(self.status)
            except ValueError:
                pass

            #TODO: Factorise
            if self.status != SYNC_AIRSYNC_STATUS_SUCCESS:
                self.add_error_message(_(u"There was an error during synchronization phase. Try again later."))
                if self.status == SYNC_AIRSYNC_STATUS_INVALID_SYNCKEY:
                    SyncKeyHistory.back_to_previous_key(client)
                return

#            commands_node = xml2.find('%(ns0)sCollections/%(ns0)sCollection/%(ns0)sCommands' % d_ns)
            commands_node = xml2_collection_find('%(ns0)sCommands' % d_ns)
            add_nodes     = commands_node.findall('%(ns0)sAdd' % d_ns)    if commands_node else []
            change_nodes  = commands_node.findall('%(ns0)sChange' % d_ns) if commands_node else []
            delete_nodes  = commands_node.findall('%(ns0)sDelete' % d_ns) if commands_node else []

            create = exch_map_manager.create

            #TODO: Singular / Plural
            self.add_info_message(_(u"There is %s new items from the server")     % len(add_nodes))
            self.add_info_message(_(u"There is %s changed items from the server") % len(change_nodes))
            self.add_info_message(_(u"There is %s deleted items from the server") % len(delete_nodes))

            if user.has_perm_to_create(Contact):
                for add_node in add_nodes:
                    add_node_find = add_node.find

                    server_id_pk  = add_node_find('%(ns0)sServerId' % d_ns).text#This is the object pk on the server map it whith cremepk
                    app_data      = add_node_find('%(ns0)sApplicationData' % d_ns)
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
                    self.add_history_create_in_creme(contact)

                    try:
                        create(creme_entity_id=contact.id, exchange_entity_id=server_id_pk, synced=True, user=user)
                        self.add_message(MessageSucceedContactAdd(contact=contact, message=_(u"Successfully created %s") % contact))
                    except IntegrityError:
                        error(u"Contact : %s (pk=%s) created twice and only one in the mapping", contact, contact.pk)#TODO:Make a merge UI?
                        self.add_error_message(u"TODO: REMOVE ME : Contact : %s (pk=%s) created twice and only one in the mapping" % (contact, contact.pk))

    #                create(creme_entity_id=contact.id, exchange_entity_id=server_id_pk, synced=True, user=user)
    ##                debug("Create a contact: %s", contact)
    #                self.add_success_message(_(u"Successfully created %s") % contact)
            else:
                self.add_error_message(SYNC_ERR_VERBOSE[SYNC_ERR_CREME_PERMISSION_DENIED_CREATE])


            for change_node in change_nodes:
                c_server_id = change_node.find('%(ns0)sServerId' % d_ns).text
                contact     = None
                
                try:
                    contact_mapping = exch_map_manager_get(exchange_entity_id=c_server_id, user=user)
                    contact = contact_mapping.get_entity()
                except CremeExchangeMapping.DoesNotExist:
                    error("Server changes object with server_id: %s when creme hasn't it or doesn't belongs to %s", c_server_id, user)
                    continue #TODO: Think about creating it ? / got a mapping issue ?

                if contact is not None:
                    if not contact.can_change(user):
                        self.add_error_message(SYNC_ERR_VERBOSE[SYNC_ERR_CREME_PERMISSION_DENIED_CHANGE_SPECIFIC] % contact)
                        continue

                    if not IS_SERVER_MASTER and contact_mapping.is_creme_modified:
                        #We don't update the contact because creme modified it and it's the master
                        continue

                    update_data = {}
                    app_data_node = change_node.find('%(ns0)sApplicationData' % d_ns)
                    for ns, field_dict in CREME_CONTACT_MAPPING.iteritems():
                        for c_field, x_field in field_dict.iteritems():
                            node = app_data_node.find('%(ns1)s%(x_field)s' % {'x_field': x_field, 'ns1': ns1})
                            if node is not None:
                                if callable(c_field):
                                    c_field = c_field(needs_attr=True)

                                update_data[c_field] = node.text

                    debug("Update %s with %s", contact, update_data)

                    history = self.add_history_update_in_creme(contact, None)

                    update_contact(contact, update_data, user, history)

#                    history.changes = update_data.iteritems()
#                    history.save()
#                    self.add_history_update_in_creme(contact, update_data)
                    self.add_message(MessageSucceedContactUpdate(contact, _(u"Successfully updated %(contact)s") % {'contact': contact}, update_data))

                    #Server is the master so we unset the creme flag to prevent creme modifications
                    contact_mapping.is_creme_modified = False
                    contact_mapping.save()

            for delete_node in delete_nodes:
                #TODO: Hum, consider refactor this part with changes_nodes
                c_server_id = delete_node.find('%(ns0)sServerId' % d_ns).text
                contact     = None
                c_x_mapping = None
                try:
                    c_x_mapping = exch_map_manager_get(exchange_entity_id=c_server_id, user=user)
                    contact = c_x_mapping.get_entity()
                except CremeExchangeMapping.DoesNotExist:
                    error("Server delete object with server_id: %s when creme hasn't it or doesn't belongs to %s", c_server_id, user)
                    continue #TODO: Think about creating it ? / got a mapping issue ?

                if contact is not None:
                    if not contact.can_delete(user):
                        self.add_error_message(SYNC_ERR_VERBOSE[SYNC_ERR_CREME_PERMISSION_DENIED_DELETE_SPECIFIC] % contact)
                        continue

                    if not IS_SERVER_MASTER and c_x_mapping.is_creme_modified:
                        #We don't delete the contact because creme modified it and it's the master
                        debug("Creme modified %s, when the server deletes it", contact)
                        self.add_info_message(_(u"The server deletes the contact but Creme modified it, so it will be synced at the next synchronization."))
                    else:
                        debug("Deleting %s", contact)
                        try:
                            contact.delete()
                        except Contact.CanNotBeDeleted, err:
                            self.add_error_message(_(u"%s. For keeping a consistent state between Creme and the server, this contact have be added again on the server. If you want to avoid this, delete the contact in Creme and synchronize again.") % err)
                        else:
                            self.add_history_delete_in_creme(contact)
                            self.add_success_message(_(u"Successfully deleted %s") % contact)
                    c_x_mapping.delete()


#        q_not_synced = ~Q(pk__in=exch_map_manager.filter(synced=True).values_list('creme_entity_id', flat=True))
#        add_objects = map(lambda c:  add_object(c, lambda cc: serialize_contact(cc, reverse_ns)), Contact.objects.filter(q_not_synced & Q(is_deleted=False)))

        objects = list(chain(get_add_objects(reverse_ns, user, self), get_change_objects(reverse_ns, user, self), get_deleted_objects(user, self)))

        if objects:#No need to send empty sync
            xml3 = super(AirSync, self).send({'class':     "Contacts",
                                              'synckey':   self.last_synckey,
                                              'server_id': server_id,
                                              'fetch':     False,
                                              'objects':   objects,
                                              'extra_ns':  extra_ns
                                              },
                                              headers={
                                                "X-Ms-Policykey": policy_key
                                              })

            xml_err_status = xml3.find('%(ns0)sStatus' % d_ns)#If status is present here there is an error
            if xml_err_status is not None:
                self.add_error_message(_(u"There was an error during synchronization phase. Try again later. (%s)") % xml_err_status.text)

                try:
                    err_status = int(xml_err_status.text)
                except:
                    err_status = 0

                if err_status == SYNC_AIRSYNC_STATUS_INVALID_SYNCKEY:
                    SyncKeyHistory.back_to_previous_key(client)
                return


            xml3_collection = xml3.find('%(ns0)sCollections/%(ns0)sCollection' % d_ns)
            xml3_collection_find = xml3_collection.find

    #        print "\n\n xml3 :", tostring(xml3), "\n\n"

            self.last_synckey = xml3_collection_find('%(ns0)sSyncKey' % d_ns).text
            self.status       = xml3_collection_find('%(ns0)sStatus' % d_ns).text
            responses         = xml3_collection_find('%(ns0)sResponses' % d_ns)

            SyncKeyHistory.objects.create(client=client, sync_key=self.last_synckey)

            try:
                self.status = int(self.status)
            except ValueError:
                pass

            #TODO: Factorise
            if self.status != SYNC_AIRSYNC_STATUS_SUCCESS:
                self.add_error_message(_(u"There was an error during synchronization phase. Try again later."))
                if self.status == SYNC_AIRSYNC_STATUS_INVALID_SYNCKEY:
                    SyncKeyHistory.back_to_previous_key(client)
                return

            if responses is not None:
                add_nodes = responses.findall('%(ns0)sAdd' % d_ns)#Present if the "Add" operation succeeded
                add_stack = self.synced['Add']
                add_stack_append = add_stack.append

                for add_node in add_nodes:
                    add_node_find = add_node.find
                    add_stack_append({
                        'client_id' : add_node_find('%(ns0)sClientId' % d_ns).text, #Creme PK
                        'server_id' : add_node_find('%(ns0)sServerId' % d_ns).text, #Server PK
                        'status'    : add_node_find('%(ns0)sStatus'   % d_ns).text,
                    })

                change_nodes = responses.findall('%(ns0)sChange' % d_ns)#Present if the "Change" operation failed
                change_stack = self.synced['Change']
                change_stack_append = change_stack.append
                for change_node in change_nodes:
                    change_node_find = change_node.find
                    change_stack_append({
                        'server_id' : change_node_find('%(ns0)sServerId' % d_ns).text, #Server PK
                        'status'    : change_node_find('%(ns0)sStatus'   % d_ns).text, #Error status
                    })

            
def add_object(o, serializer):
    return "<Add><ClientId>%s</ClientId><ApplicationData>%s</ApplicationData></Add>" % (o.id, serializer(o))

def get_add_objects(reverse_ns, user, airsync_cmd):
    q_not_synced = ~Q(pk__in=CremeExchangeMapping.objects.filter(synced=True).values_list('creme_entity_id', flat=True))
    objects = []

    add_message      = airsync_cmd.add_message
    add_info_message = airsync_cmd.add_info_message
    objects_append   = objects.append
    add_history_create_on_server = airsync_cmd.add_history_create_on_server

    for contact in Contact.objects.filter(q_not_synced & Q(is_deleted=False, user=user)):
        if contact.can_view(user):
            add_message(MessageInfoContactAdd(contact, _(u"Adding %s on the server") % contact))
            add_history_create_on_server(contact)
            objects_append(add_object(contact, lambda cc: serialize_contact(cc, reverse_ns)))
        else:
            add_info_message(_(u"The contact <%s> was not added on the server because you haven't the right to view it") % contact.allowed_unicode(user))

    return objects
#    return map(lambda c:  add_object(c, lambda cc: serialize_contact(cc, reverse_ns)), Contact.objects.filter(q_not_synced & Q(is_deleted=False)))


def change_object(server_id, o, serializer):
    return "<Change><ServerId>%s</ServerId><ApplicationData>%s</ApplicationData></Change>" % (server_id, serializer(o))

def get_change_objects(reverse_ns, user, airsync_cmd):
#    modified_ids = CremeExchangeMapping.objects.filter(is_creme_modified=True, user=user).values_list('creme_entity_id', flat=True)

    #modified_ids a dict with creme_entity_id value as key and corresponding exchange_entity_id as value
    modified_ids = dict(CremeExchangeMapping.objects.filter(is_creme_modified=True, user=user).values_list('creme_entity_id', 'exchange_entity_id'))

    objects = []

    debug(u"Change object ids : %s", modified_ids)

    add_info_message = airsync_cmd.add_info_message
    objects_append   = objects.append
    add_history_update_on_server = airsync_cmd.add_history_update_on_server


    for contact in Contact.objects.filter(id__in=modified_ids.keys()):
        if contact.can_view(user):
            add_info_message(_(u"Sending changes of %s on the server") % contact)
            add_history_update_on_server(contact, None)#TODO: Add update information....
            objects_append(change_object(modified_ids[contact.id], contact, lambda cc: serialize_contact(cc, reverse_ns)))#Naive version send all attribute even it's not modified
        else:
            add_info_message(_(u"The contact <%s> was not updated on the server because you haven't the right to view it") % contact.allowed_unicode(user))

    debug(u"Change object : %s", objects)

    return objects

def delete_object(server_id):
    return "<Delete><ServerId>%s</ServerId></Delete>" % server_id

def get_deleted_objects(user, airsync_cmd):
#    deleted_ids = CremeExchangeMapping.objects.filter(was_deleted=True, user=user).values_list('exchange_entity_id', flat=True)
    deleted_ids = CremeExchangeMapping.objects.filter(was_deleted=True, user=user).values_list('exchange_entity_id', 'creme_entity_repr')
    objects = []
    
#    for server_id in deleted_ids:
#        objects.append(delete_object(server_id))

    add_info_message = airsync_cmd.add_info_message
    objects_append   = objects.append
    add_history_delete_on_server = airsync_cmd.add_history_delete_on_server

    for server_id, entity_repr in deleted_ids:
        if entity_repr is not None:
            add_history_delete_on_server(entity_repr)
            add_info_message(_(u"Deleting %s on the server") % entity_repr)
        objects_append(delete_object(server_id))
        
    return objects







        
