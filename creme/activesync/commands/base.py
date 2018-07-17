# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2017  Hybird
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

from collections import defaultdict
from httplib import socket
import logging

import restkit.errors

from django.conf import settings
from django.template.loader import render_to_string

from creme.activesync import errors
from creme.activesync.connection import Connection
from creme.activesync.messages import _INFO, _ERROR, _SUCCESS, MessageInfo, MessageSucceed, MessageError
from creme.activesync.models.active_sync import UserSynchronizationHistory, CREATE, UPDATE, DELETE, IN_CREME, ON_SERVER
from creme.activesync.wbxml.codec import WBXMLEncoder, WBXMLDecoder, prettify
from creme.activesync.wbxml.dtd import AirsyncDTD_Reverse, AirsyncDTD_Forward


logger = logging.getLogger(__name__)
ACTIVE_SYNC_DEBUG = settings.ACTIVE_SYNC_DEBUG  # TODO: remove


class Base:
    template_name = u'overloadme.xml'  # XML template to send to the server
    command       = u'OVERLOADME'      # Associated command
    encoder       = lambda s, x: WBXMLEncoder(AirsyncDTD_Reverse).encode(x)  # xml to wbxml encoder
    decoder       = lambda s, x: WBXMLDecoder(AirsyncDTD_Forward).decode(x)  # wbxml to xml decoder

    def __init__(self, url, login, pwd, device_id, user):
        self.url = url
        self.user = user
        self.login = login
        self.password = pwd
        self.device_id = device_id
        self._data = {
                        'debug': {
                                    'xml':    [],
                                    'errors': [],
                                 },
                     }
        self._messages = defaultdict(list)

    ###### UI helpers #######
    def add_message(self, msg):
        self._messages[msg.type].append(msg)

    def add_info_message(self, msg, **kwargs):
        self._messages[_INFO].append(MessageInfo(message=msg, **kwargs))

    def add_success_message(self, msg, **kwargs):
        self._messages[_SUCCESS].append(MessageSucceed(message=msg, **kwargs))

    def add_error_message(self, msg, **kwargs):
        self._messages[_ERROR].append(MessageError(message=msg, **kwargs))

    def get_messages(self, level):
        return self._messages[level]

    def messages(self):
        return self._messages.items()

    def get_info_messages(self):
        return self._messages[_INFO]

    def get_success_messages(self):
        return self._messages[_SUCCESS]

    def get_error_messages(self):
        return self._messages[_ERROR]
    ###### End UI helpers #######

    # History helpers
    def _add_history(self, entity, where, type, entity_changes=None):
        return UserSynchronizationHistory._add(self.user, entity, where, type, entity_changes)

    def add_history_create_in_creme(self, entity):
        return self._add_history(entity, IN_CREME, CREATE)

    def add_history_create_on_server(self, entity):
        return self._add_history(entity, ON_SERVER, CREATE)

    def add_history_update_in_creme(self, entity, entity_changes):
        return self._add_history(entity, IN_CREME, UPDATE, entity_changes)

    def add_history_update_on_server(self, entity, entity_changes):
        return self._add_history(entity, ON_SERVER, UPDATE, entity_changes)

    def add_history_delete_in_creme(self, entity):
        return self._add_history(entity, IN_CREME, DELETE)

    def add_history_delete_on_server(self, entity):
        return self._add_history(entity, ON_SERVER, DELETE)

    def update_histories_on_delete(self, entity_pk):
        UserSynchronizationHistory.objects.filter(entity_pk=entity_pk).update(entity_pk=None)
    #End history helpers

    def _create_connection(self, *args, **kwargs):
        self.connection = Connection.create(self.url, self.login, self.password, *args, **kwargs)

    def _encode(self, content):
        if settings.ACTIVE_SYNC_DEBUG:
            # print u"Request: %s" % content
            msg = u'Request: %s' % content
            logger.warning(msg)
            self._data['debug']['xml'].append(msg)

        return self.encoder(str(content.encode('utf-8'))) # TODO: Verify side effects

    def _decode(self, content):
        try:
            decoded = self.decoder(content)
        except Exception as e:
            logger.warning('Error while decoding reponse (%s)', e)
            raise errors.CremeActiveSyncError(errors.SYNC_ERR_NOT_FOUND)
#        return fromstring(str(self.decoder(content)))#Trick to use ElementTree instead of libxml2 in waiting for own ElementTree parser

        if settings.ACTIVE_SYNC_DEBUG:
            # print u"Response: %s" % prettify(self.decoder(content))
            msg = u'Response: %s' % prettify(decoded)
            logger.warning(msg)
            self._data['debug']['xml'].append(msg)

        return decoded

    def _send(self, encoded_content, *args, **kwargs):
        try:
            return self.connection.send(self.command, encoded_content, self.device_id, *args, **kwargs)
        except restkit.errors.Unauthorized as e:
            self._data['debug']['errors'].append(e.msg)
            raise errors.CremeActiveSyncError(errors.SYNC_ERR_FORBIDDEN)
        except (socket.gaierror, socket.error) as e:
            self._data['debug']['errors'].append(e.strerror)
            raise errors.CremeActiveSyncError(errors.SYNC_ERR_CONNECTION)
        except restkit.errors.ResourceNotFound as e:
            self._data['debug']['errors'].append(e.msg)
            raise errors.CremeActiveSyncError(errors.SYNC_ERR_NOT_FOUND)
        except restkit.errors.RequestError as e:
            self._data['debug']['errors'].append(str(e))
            raise errors.CremeActiveSyncError(errors.SYNC_ERR_REQUEST)
        except Exception as e:
            self._data['debug']['errors'].append(str(e))
            raise errors.CremeActiveSyncError(errors.SYNC_ERR)

    def send(self, template_dict, *args, **kwargs):
        content = render_to_string(self.template_name, template_dict)
        encoded_content = self._encode(content)
        response = self._send(encoded_content, *args, **kwargs)

        return self._decode(response)
