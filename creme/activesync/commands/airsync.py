# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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
import logging
#from xml.etree.ElementTree import tostring

from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.db.utils import IntegrityError
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext_lazy as _ #TODO: ugettext instead ??

from creme.creme_core.models.entity import CremeEntity

from ..constants import (CONFLICT_SERVER_MASTER, SYNC_AIRSYNC_STATUS_SUCCESS, 
                         SYNC_AIRSYNC_STATUS_INVALID_SYNCKEY,
                         SYNC_AIRSYNC_STATUS_CLIENT_SERV_CONV_ERR,
                         SYNC_FOLDER_TYPE_CONTACT, SYNC_FOLDER_TYPE_APPOINTMENT)
from ..models import (CremeExchangeMapping, CremeClient, SyncKeyHistory)
from ..mappings import CREME_AS_MAPPING, FOLDERS_TYPES_CREME_TYPES_MAPPING
from ..messages import MessageSucceedContactAdd, MessageSucceedContactUpdate, MessageInfoContactAdd
from ..errors import (SYNC_ERR_VERBOSE, SYNC_ERR_CREME_PERMISSION_DENIED_CREATE,
                      SYNC_ERR_CREME_PERMISSION_DENIED_CHANGE_SPECIFIC,
                      SYNC_ERR_CREME_PERMISSION_DENIED_DELETE_SPECIFIC)
from ..utils import is_user_sync_calendars, is_user_sync_contacts
from .base import Base


logger = logging.getLogger(__name__)


class AirSync(Base):
    template_name = "activesync/commands/xml/airsync/request_min.xml"
    command       = "Sync"
    CONFLICT_MODE = settings.CONFLICT_MODE

    def __init__(self, *args, **kwargs):
        super(AirSync, self).__init__(*args, **kwargs)
        self._create_connection()

    def _filter_folders(self, folders):
        if not is_user_sync_calendars(self.user):
            folders = filter(lambda f: not f.type==SYNC_FOLDER_TYPE_APPOINTMENT, folders)

        if not is_user_sync_contacts(self.user):
            folders = filter(lambda f: not f.type==SYNC_FOLDER_TYPE_CONTACT, folders)

        return folders

    def send(self, policy_key, folders, synckey=None, fetch=True, headers=None):
        for folder in self._filter_folders(folders):
            self.send_for_folder(policy_key, folder, synckey, fetch, headers)
            folder.save()

    def send_for_folder(self, policy_key, folder, synckey=None, fetch=True, headers=None):
        """
            @param policy_key string set in the header to be authorized
            @param folder AS_Folder folder which will be synchronized
            @param synckey None to fetch all server changes or last synckey supplied by server
            @param fetch True for fetching changes False for current pushing changes
            @param header a dict of extra http header parameters
        """

        creme_model = FOLDERS_TYPES_CREME_TYPES_MAPPING.get(folder.type)
        creme_model_AS_values = CREME_AS_MAPPING.get(creme_model)

        if creme_model is None or creme_model_AS_values is None:
            return#Folder type is not implemented

        user                 = self.user
        exch_map_manager     = CremeExchangeMapping.objects
        exch_map_manager_get    = exch_map_manager.get
        exch_map_manager_create = exch_map_manager.create
        exch_map_manager_get_or_create = exch_map_manager.get_or_create
#        self.last_synckey    = synckey
        self.last_synckey    = folder.sync_key
        CONFLICT_MODE        = self.CONFLICT_MODE
        IS_SERVER_MASTER     = True if CONFLICT_MODE==CONFLICT_SERVER_MASTER else False
        client               = CremeClient.objects.get(user=user)
        folder.supported = []
        folder.entities = []
        creme_model_verbose_name = creme_model._meta.verbose_name
        ct_creme_model = ContentType.objects.get_for_model(creme_model)
        mapping = creme_model_AS_values['mapping']
        add_error_message = self.add_error_message

        http_headers = {"X-Ms-Policykey": policy_key}
        if headers is not None:
            http_headers.update(headers)

        options = {
            'Conflict': CONFLICT_MODE,
        }

#        self.synced = {
#                        "Add":[],
#                        "Change": [],
#                      }

        #Gathering all required namespaces
        namespaces = mapping.keys()
        extra_ns   = dict(("A%s" % i, v) for i, v in enumerate(namespaces))
        reverse_ns = dict((v,k) for k, v in extra_ns.iteritems())

        reverse_ns_get = reverse_ns.get
        folder_supported_append = folder.supported.append

        for prefix, ns in mapping.iteritems():
            for item in ns.values():
                ns_prefix = reverse_ns_get(prefix)
                folder_supported_append("<%s%s/>" % ('%s:' % ns_prefix if ns_prefix else '', item))

        ns0 = "{AirSync:}"
        d_ns = {'ns0': ns0}

        if synckey in (0, 1, None):
#            supported = []
#            supported_append = supported.append
#
#            for prefix, ns in CREME_CONTACT_MAPPING.iteritems():
#                for item in ns.values():
#                    ns_prefix = reverse_ns_get(prefix)
#                    supported_append("<%s%s/>" % ('%s:' % ns_prefix if ns_prefix else '', item))

            xml = super(AirSync, self).send({'folder': folder, 'synckey': 0, 'extra_ns': extra_ns}, headers=http_headers)

            err_status_xml = xml.find('%(ns0)sStatus' % d_ns)
            if err_status_xml:
                #If the status is at the root it seems there is an error
                add_error_message(_(u"There was an error during synchronization phase. Error code : %s") % err_status_xml.text)
                return

            collection = xml.find('%(ns0)sCollections/%(ns0)sCollection' % d_ns)
            collection_find = collection.find

            self.last_synckey = folder.sync_key = collection_find('%(ns0)sSyncKey' % d_ns).text
            self.status       = collection_find('%(ns0)sStatus' % d_ns).text
#            server_id         = collection_find('%(ns0)sCollectionId' % d_ns).text

            SyncKeyHistory.objects.create(client=client, sync_key=self.last_synckey)

            try:
                self.status = int(self.status)
            except ValueError:
                pass ###TODO: ???


            if self.status != SYNC_AIRSYNC_STATUS_SUCCESS:
                add_error_message(_(u"There was an error during synchronization phase. Try again later."))
                return

        if fetch:
            ################
            ##SERVER PART ##
            ################
            xml2 = super(AirSync, self).send({'folder': folder, 'synckey': self.last_synckey, 'fetch': True, 'extra_ns': extra_ns, 'options': options}, headers=http_headers)

#            print "\n\n xml2 :", tostring(xml2), "\n\n"

            xml2_collection      = xml2.find('%(ns0)sCollections/%(ns0)sCollection' % d_ns)
            xml2_collection_find = xml2_collection.find

#            self.last_synckey = xml2.find('%(ns0)sCollections/%(ns0)sCollection/%(ns0)sSyncKey' % d_ns).text
#            self.status       = xml2.find('%(ns0)sCollections/%(ns0)sCollection/%(ns0)sStatus' % d_ns).text

            self.last_synckey = folder.sync_key = xml2_collection_find('%(ns0)sSyncKey' % d_ns).text
            self.status       = xml2_collection_find('%(ns0)sStatus' % d_ns).text

            SyncKeyHistory.objects.create(client=client, sync_key=self.last_synckey)

            try:
                self.status = int(self.status)
            except ValueError:
                pass

            #TODO: Factorise
            if self.status != SYNC_AIRSYNC_STATUS_SUCCESS:
                add_error_message(_(u"There was an error during synchronization phase. Try again later."))
                if self.status == SYNC_AIRSYNC_STATUS_INVALID_SYNCKEY:
                    SyncKeyHistory.back_to_previous_key(client)
                return

#            commands_node = xml2.find('%(ns0)sCollections/%(ns0)sCollection/%(ns0)sCommands' % d_ns)
            commands_node = xml2_collection_find('%(ns0)sCommands' % d_ns)
            add_nodes     = commands_node.findall('%(ns0)sAdd' % d_ns)    if commands_node else []
            change_nodes  = commands_node.findall('%(ns0)sChange' % d_ns) if commands_node else []
            delete_nodes  = commands_node.findall('%(ns0)sDelete' % d_ns) if commands_node else []

            #TODO: Singular / Plural
            self.add_info_message(_(u"There is %(count)s new %(model)s from the server")     % {'count': len(add_nodes),    'model': creme_model_verbose_name})
            self.add_info_message(_(u"There is %(count)s changed %(model)s from the server") % {'count': len(change_nodes), 'model': creme_model_verbose_name})
            self.add_info_message(_(u"There is %(count)s deleted %(model)s from the server") % {'count': len(delete_nodes), 'model': creme_model_verbose_name})

            save_entity = creme_model_AS_values['save']

            if user.has_perm_to_create(creme_model):
                for add_node in add_nodes:
                    add_node_find = add_node.find

                    server_id_pk  = add_node_find('%(ns0)sServerId' % d_ns).text#This is the object pk on the server map it whith cremepk
                    app_data      = add_node_find('%(ns0)sApplicationData' % d_ns)

                    data = {'user': user}
                    if app_data is not None:
                        app_data_find = app_data.find
                        for ns, field_dict in mapping.iteritems():
                            for c_field, x_field in field_dict.iteritems():
                                d = app_data_find('{%s}%s' % (ns, x_field))
                                if d is not None:
                                    if callable(c_field):
                                        c_field = c_field(needs_attr=True)

                                    if c_field and c_field.strip() != '':
                                        data[c_field] = smart_unicode(d.text)
                    else:
                        for ns, field_dict in mapping.iteritems():
                            for c_field, x_field in field_dict.iteritems():
                                if callable(c_field):
                                    c_field = c_field(needs_attr=True)
                                data[c_field] = u""

                    uid_google = data['UID']
                    from creme.activesync.models import EntityASData
                    uids = EntityASData.objects.filter(field_value=uid_google).order_by('-id')
                    if uids.count() > 0:
                        entity= uids[0].entity
                        try:
                            entity_mapping = exch_map_manager_get(creme_entity_id=entity.id, user=user)
                            entity_mapping.exchange_entity_id = server_id_pk
                            entity_mapping.synced = True
                            entity_mapping.save()
                        except Exception :
                            pass
                    else:
                        entity = save_entity(data, user, folder)
                        self.add_history_create_in_creme(entity)

#                    entity = save_entity(data, user, folder)
#                    self.add_history_create_in_creme(entity)

                        try:
                            #exch_map_manager_create(creme_entity_id=entity.id, exchange_entity_id=server_id_pk, synced=True, user=user, creme_entity_ct=ct_creme_model)
                            obj, created = exch_map_manager_get_or_create(creme_entity_id=entity.id, exchange_entity_id=server_id_pk,
                                user=user, creme_entity_ct=ct_creme_model)
                            obj.synced = True
                            obj.save()
                            msg = _(u"Successfully created %s")  if created else _(u"WARNING : %s was already created")
                            self.add_message(MessageSucceedContactAdd(contact=entity, message=msg % entity))
                        except IntegrityError:
                            logger.error(u"Entity : %s (pk=%s) big error in the mapping", entity, entity.pk)#TODO:Make a merge UI?
                            add_error_message(u"TODO: REMOVE ME : Entity : %s (pk=%s) big error in the mapping" % (entity, entity.pk))

            else:
                add_error_message(SYNC_ERR_VERBOSE[SYNC_ERR_CREME_PERMISSION_DENIED_CREATE])


            update_entity = creme_model_AS_values['update']
            for change_node in change_nodes:
                c_server_id = change_node.find('%(ns0)sServerId' % d_ns).text
                entity     = None

                try:
                    entity_mapping = exch_map_manager_get(exchange_entity_id=c_server_id, user=user)
                    entity = entity_mapping.get_entity()
                except CremeExchangeMapping.DoesNotExist:
                    logger.error("Server changes object with server_id: %s when creme hasn't it or doesn't belongs to %s", c_server_id, user)
                    continue #TODO: Think about creating it ? / got a mapping issue ?

                if entity is not None:
                    if not user.has_perm_to_change(entity):
                        add_error_message(SYNC_ERR_VERBOSE[SYNC_ERR_CREME_PERMISSION_DENIED_CHANGE_SPECIFIC] % entity)
                        continue

                    if not IS_SERVER_MASTER and entity_mapping.is_creme_modified:
                        #We don't update the entity because creme modified it and it's the master
                        continue

                    update_data = {}
                    app_data_node = change_node.find('%(ns0)sApplicationData' % d_ns)
                    if app_data_node is not None:
                        for ns, field_dict in mapping.iteritems():
                            for c_field, x_field in field_dict.iteritems():
                                node = app_data_node.find('{%(ns1)s}%(x_field)s' % {'x_field': x_field, 'ns1': ns})
                                if node is not None:
                                    if callable(c_field):
                                        c_field = c_field(needs_attr=True)

                                    update_data[c_field] = smart_unicode(node.text)
                    else:
                        for ns, field_dict in mapping.iteritems():
                            for c_field, x_field in field_dict.iteritems():
                                if callable(c_field):
                                    c_field = c_field(needs_attr=True)
                                update_data[c_field] = u""

                    logger.debug("Update %s with %s", entity, update_data)

                    history = self.add_history_update_in_creme(entity, None)

                    update_entity(entity, update_data, user, history, folder)

#                    history.changes = update_data.iteritems()
#                    history.save()
#                    self.add_history_update_in_creme(entity, update_data)
                    self.add_message(MessageSucceedContactUpdate(entity, _(u"Successfully updated %(entity)s") % {'entity': entity}, update_data))

                    #Server is the master so we unset the creme flag to prevent creme modifications
                    entity_mapping.is_creme_modified = False
                    entity_mapping.save()

            for delete_node in delete_nodes:
                #TODO: Hum, consider refactor this part with changes_nodes
                c_server_id = delete_node.find('%(ns0)sServerId' % d_ns).text
                entity     = None
                c_x_mapping = None
                try:
                    c_x_mapping = exch_map_manager_get(exchange_entity_id=c_server_id, user=user)
                    entity = c_x_mapping.get_entity()
                except CremeExchangeMapping.DoesNotExist:
                    logger.error("Server delete object with server_id: %s when creme hasn't it or doesn't belongs to %s", c_server_id, user)
                    continue #TODO: Think about creating it ? / got a mapping issue ?

                if entity is not None:
                    if not user.has_perm_to_delete(entity):
                        add_error_message(SYNC_ERR_VERBOSE[SYNC_ERR_CREME_PERMISSION_DENIED_DELETE_SPECIFIC] % entity)
                        continue

                    if not IS_SERVER_MASTER and c_x_mapping.is_creme_modified:
                        #We don't delete the entity because creme modified it and it's the master
                        logger.debug("Creme modified %s, when the server deletes it", entity)
                        self.add_info_message(_(u"The server deletes the %s but Creme modified it, so it will be synced at the next synchronization.") % creme_model_verbose_name)
                    else:
                        logger.debug("Deleting %s", entity)
                        entity_pk = entity.pk
                        try:
                            entity.delete()
                        except ProtectedError:
                            add_error_message(_(u"%(entity)s. For keeping a consistent state between Creme and the server, this %(model_verbose)s have be added again on the server. If you want to avoid this, delete the %(model_verbose)s in Creme and synchronize again.") % {'entity': entity, 'model_verbose': creme_model_verbose_name})
                        else:
                            self.add_history_delete_in_creme(entity)
                            self.add_success_message(_(u"Successfully deleted %s") % entity)
                            self.update_histories_on_delete(entity_pk)
                    c_x_mapping.delete()


        serializer = creme_model_AS_values['serializer']
        folder.entities = list(
                                chain(get_add_objects(reverse_ns, user, self, creme_model, serializer, mapping),
                                      get_change_objects(reverse_ns, user, self, creme_model, serializer, mapping),
                                      get_deleted_objects(user, self, creme_model))
                               )

        if folder.entities:#No need to send empty sync if no entities
            xml3 = super(AirSync, self).send({'folder':    folder,
                                              'synckey':   self.last_synckey,
                                              'fetch':     False,
                                              'extra_ns':  extra_ns
                                              },
                                              headers=http_headers)

            xml_err_status = xml3.find('%(ns0)sStatus' % d_ns)#If status is present here there is an error
            if xml_err_status is not None:
                add_error_message(_(u"There was an error during synchronization phase. Try again later. (%s)") % xml_err_status.text)

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

            self.last_synckey = folder.sync_key = xml3_collection_find('%(ns0)sSyncKey' % d_ns).text
            self.status       = xml3_collection_find('%(ns0)sStatus' % d_ns).text
            responses         = xml3_collection_find('%(ns0)sResponses' % d_ns)

            SyncKeyHistory.objects.create(client=client, sync_key=self.last_synckey)

            try:
                self.status = int(self.status)
            except ValueError:
                pass

            #TODO: Factorise
            if self.status != SYNC_AIRSYNC_STATUS_SUCCESS:
                add_error_message(_(u"There was an error during synchronization phase. Try again later."))
                if self.status == SYNC_AIRSYNC_STATUS_INVALID_SYNCKEY:
                    SyncKeyHistory.back_to_previous_key(client)
                return

            unchanged_server_id = ()
            if responses is not None:
                ########################################################
                # Response from server for confirm / invalidate changes
                ########################################################

                ## Add part
                rejected_add_ids = []
                rejected_add_ids_append = rejected_add_ids.append
                add_nodes = responses.findall('%(ns0)sAdd' % d_ns)#Present if the "Add" operation succeeded

                ### Registering added entities
                for add_node in add_nodes:
                    add_node_find = add_node.find
                    creme_entity_id = add_node_find('%(ns0)sClientId' % d_ns).text
                    item_status = SYNC_AIRSYNC_STATUS_SUCCESS

                    try:
                        item_status = int(add_node_find('%(ns0)sStatus' % d_ns).text)
                    except (ValueError, TypeError):
                        continue#If there is no status there was an error

                    if item_status == SYNC_AIRSYNC_STATUS_CLIENT_SERV_CONV_ERR:
                        rejected_add_ids_append(creme_entity_id)
                        continue

                    exch_map_manager_create(creme_entity_id=creme_entity_id, #Creme PK
                                            exchange_entity_id=add_node_find('%(ns0)sServerId' % d_ns).text, #Server PK
                                            synced=True,
                                            user=user,
                                            creme_entity_ct=ct_creme_model)#Create object mapping
                ###Error messages
                entities = CremeEntity.objects.filter(pk__in=rejected_add_ids)
                for entity in entities:
                    add_error_message(_(u"The server has denied to add <%s>. (It happens for example for activities which are on a read-only calendar)") % (entity))

                ## Change part
                change_nodes = responses.findall('%(ns0)sChange' % d_ns)#Present if the "Change" operation failed
                change_stack = []
                change_stack_append = change_stack.append
                rejected_change_ids = []
                rejected_change_ids_append = rejected_change_ids.append

                for change_node in change_nodes:
                    change_node_find = change_node.find

                    server_id = change_node_find('%(ns0)sServerId' % d_ns).text #Server PK

                    item_status = SYNC_AIRSYNC_STATUS_SUCCESS

                    try:
                        item_status = int(change_node_find('%(ns0)sStatus'   % d_ns).text)
                    except (ValueError, TypeError):
                        continue#If there is no status there was an error


                    if item_status == SYNC_AIRSYNC_STATUS_CLIENT_SERV_CONV_ERR:
                        rejected_change_ids_append(server_id)
                        continue

                    change_stack_append({
                        'server_id' : server_id,
                        'status'    : change_node_find('%(ns0)sStatus'   % d_ns).text, #Error status#TODO: Check the status to exclude refused entities
                    })

                ### Updating mapping only for entities actually changed on the server
                ### Ensure we actually update for the right(current) user
                unchanged_server_id = [change.get('server_id') for change in change_stack]
#                exch_map_manager.filter(Q(is_creme_modified=True, user=user) & ~Q(exchange_entity_id__in=unchanged_server_id)).update(is_creme_modified=False)

                unchanged_entities = CremeEntity.objects.filter(pk__in=exch_map_manager.filter(exchange_entity_id__in=rejected_change_ids).values_list('creme_entity_id', flat=True))
                ### Error messages
                for unchanged_entity in unchanged_entities:
                    add_error_message(_(u"The server has denied changes on <%s>. (It happens for example for activities which are on a read-only calendar)") % (unchanged_entity))

            exch_map_manager.filter(Q(is_creme_modified=True, user=user) & ~Q(exchange_entity_id__in=unchanged_server_id)).update(is_creme_modified=False)
            ## Delete part
            ### We delete the mapping for deleted entities
            ### TODO: Verify the status ?
            CremeExchangeMapping.objects.filter(was_deleted=True, user=user, creme_entity_ct=ct_creme_model).delete()


def add_object(o, serializer):
    return "<Add><ClientId>%s</ClientId><ApplicationData>%s</ApplicationData></Add>" % (o.id, serializer(o))

def get_add_objects(reverse_ns, user, airsync_cmd, creme_model, serializer, mapping):
    q_not_synced = ~Q(pk__in=CremeExchangeMapping.objects.filter(synced=True).values_list('creme_entity_id', flat=True))
    objects = []

    add_message      = airsync_cmd.add_message
    add_info_message = airsync_cmd.add_info_message
    objects_append   = objects.append
    add_history_create_on_server = airsync_cmd.add_history_create_on_server

    for entity in creme_model.objects.filter(q_not_synced & Q(is_deleted=False, user=user)):
        if user.has_perm_to_view(entity):
            add_message(MessageInfoContactAdd(entity, _(u"Adding %s on the server") % entity))
            add_history_create_on_server(entity)
#            objects_append(add_object(entity, lambda cc: serializer(cc, reverse_ns)))
            objects_append(add_object(entity, lambda cc: serializer(cc, mapping)))
        else:
            add_info_message(_(u"The entity <%s> was not added on the server because you haven't the right to view it") % entity.allowed_unicode(user))

    return objects

def change_object(server_id, o, serializer):
    return "<Change><ServerId>%s</ServerId><ApplicationData>%s</ApplicationData></Change>" % (server_id, serializer(o))

def get_change_objects(reverse_ns, user, airsync_cmd, creme_model, serializer, mapping):
#    modified_ids = CremeExchangeMapping.objects.filter(is_creme_modified=True, user=user).values_list('creme_entity_id', flat=True)

    #modified_ids a dict with creme_entity_id value as key and corresponding exchange_entity_id as value
    modified_ids = dict(CremeExchangeMapping.objects.filter(is_creme_modified=True, user=user, was_deleted=False).values_list('creme_entity_id', 'exchange_entity_id'))

    objects = []

    logger.debug(u"Change object ids : %s", modified_ids)

    add_info_message = airsync_cmd.add_info_message
    objects_append   = objects.append
    add_history_update_on_server = airsync_cmd.add_history_update_on_server

    for entity in creme_model.objects.filter(id__in=modified_ids.keys()):
        if user.has_perm_to_view(entity):
            add_info_message(_(u"Sending changes of %s on the server") % entity)
            add_history_update_on_server(entity, None)#TODO: Add update information....
            objects_append(change_object(modified_ids[entity.id], entity, lambda cc: serializer(cc, mapping)))#Naive version send all attribute even it's not modified
        else:
            add_info_message(_(u"The entity <%s> was not updated on the server because you haven't the right to view it") % entity.allowed_unicode(user))

    logger.debug(u"Change object : %s", objects)

    return objects

def delete_object(server_id):
    return "<Delete><ServerId>%s</ServerId></Delete>" % server_id

def get_deleted_objects(user, airsync_cmd, creme_model):
#    deleted_ids = CremeExchangeMapping.objects.filter(was_deleted=True, user=user).values_list('exchange_entity_id', flat=True)
    ct = ContentType.objects.get_for_model(creme_model)
    deleted_ids = CremeExchangeMapping.objects.filter(was_deleted=True, user=user, creme_entity_ct=ct).values_list('exchange_entity_id', 'creme_entity_repr', 'creme_entity_id')
    objects = []

    add_info_message = airsync_cmd.add_info_message
    objects_append   = objects.append
    add_history_delete_on_server = airsync_cmd.add_history_delete_on_server
    update_histories_on_delete = airsync_cmd.update_histories_on_delete

    for server_id, entity_repr, creme_entity_id in deleted_ids:
        if entity_repr is not None:
            add_history_delete_on_server((entity_repr, ct))
            add_info_message(_(u"Deleting %s on the server") % entity_repr)
            update_histories_on_delete(creme_entity_id)
        objects_append(delete_object(server_id))

    return objects
