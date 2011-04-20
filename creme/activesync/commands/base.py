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
from collections import defaultdict

import libxml2
import restkit.errors
from xml.etree.ElementTree import fromstring, tostring
from httplib import socket

from django.conf import settings
from django.template.loader import render_to_string

from activesync.errors import SYNC_ERR_FORBIDDEN, CremeActiveSyncError, SYNC_ERR_CONNECTION, SYNC_ERR_NOT_FOUND
from activesync.models.active_sync import UserSynchronizationHistory, CREATE, UPDATE, DELETE, IN_CREME, ON_SERVER
from activesync.wbxml.dtd import AirsyncDTD_Reverse
from activesync.wbxml.codec2 import WBXMLEncoder

from activesync.connection import Connection
from activesync.wbxml.converters import XMLToWBXML, WBXMLToXML

from activesync.messages import _INFO, _ERROR, _SUCCESS, MessageInfo, MessageSucceed, MessageError

ACTIVE_SYNC_DEBUG = settings.ACTIVE_SYNC_DEBUG

class Base(object):
    template_name = u"overloadme.xml" #XML template to send to the server
    command       = u"OVERLOADME"     #Associated command
#    encoder       = lambda s, x : XMLToWBXML(x) # xml to wbxml encoder
    encoder       = lambda s, x : WBXMLEncoder(AirsyncDTD_Reverse).encode(x) # xml to wbxml encoder
    decoder       = lambda s, x : WBXMLToXML(x) # wbxml to xml decoder

    def __init__(self, url, login, pwd, device_id, user):
        self.url       = url
        self.user      = user
        self.login  = login
        self.password  = pwd
        self.device_id = device_id
        self._data     = {
            'debug': {
                'xml': [],
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
        return self._messages.iteritems()

    def get_info_messages(self):
        return self._messages[_INFO]

    def get_success_messages(self):
        return self._messages[_SUCCESS]

    def get_error_messages(self):
        return self._messages[_ERROR]
    ###### End UI helpers #######

    #History helpers
    def _add_history(self, entity, where, type, entity_changes=None):
        return UserSynchronizationHistory._add(self.user, entity, where, type)

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
    #End history helpers

    def _create_connection(self, *args, **kwargs):
        self.connection = Connection.create(self.url, self.login, self.password, *args, **kwargs)

    def _encode(self, content):
        print "\n==Request==\n",content,"\n"
        
        if ACTIVE_SYNC_DEBUG:
            self._data['debug']['xml'].append(u"Request: %s" % content)

        return self.encoder(str(content.encode('utf-8')))#TODO: Verify side effects
#        return self.encoder(content)
#        return self.encoder(libxml2.parseDoc(content))

    def _decode(self, content):
#        return self.decoder(content)
        print "\n==Response==\n",str(self.decoder(content)),"\n"

        if ACTIVE_SYNC_DEBUG:
            self._data['debug']['xml'].append(u"Response: %s" % str(self.decoder(content)))

#        print "\n==Response==\n",tostring(fromstring(str(self.decoder(content)))),"\n"
        return fromstring(str(self.decoder(content)))#Trick to use ElementTree instead of libxml2 in waiting for own ElementTree parser

    def _send(self, encoded_content, *args, **kwargs):
        try:
            return self.connection.send(self.command, encoded_content, self.device_id, *args, **kwargs)
        except restkit.errors.Unauthorized, err:
            self._data['debug']['errors'].append(err.msg)
            raise CremeActiveSyncError(SYNC_ERR_FORBIDDEN)
        except (socket.gaierror, socket.error), err:
            self._data['debug']['errors'].append(err.strerror)
            raise CremeActiveSyncError(SYNC_ERR_CONNECTION)
        except restkit.errors.ResourceNotFound, err:
            self._data['debug']['errors'].append(err.msg)
            raise CremeActiveSyncError(SYNC_ERR_NOT_FOUND)

    def send(self, template_dict, *args, **kwargs):
        content = render_to_string(self.template_name, template_dict)
#        print "xml sended :\n", content,"\n\n"
        encoded_content = self._encode(content)
        response = self._send(encoded_content, *args, **kwargs)
#        print "wbxml received:\n", response,"\n\n"
        return self._decode(response)