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

import libxml2
import restkit.errors
from xml.etree.ElementTree import fromstring, tostring

from activesync.errors import SYNC_ERR_FORBIDDEN, CremeActiveSyncError
from activesync.wbxml.dtd import AirsyncDTD_Reverse
from activesync.wbxml.codec2 import WBXMLEncoder

from django.template.loader import render_to_string

from activesync.connection import Connection
from activesync.wbxml.converters import XMLToWBXML, WBXMLToXML

class Base(object):
    template_name = u"overloadme.xml" #XML template to send to the server
    command       = u"OVERLOADME"     #Associated command
#    encoder       = lambda s, x : XMLToWBXML(x) # xml to wbxml encoder
    encoder       = lambda s, x : WBXMLEncoder(AirsyncDTD_Reverse).encode(x) # xml to wbxml encoder
    decoder       = lambda s, x : WBXMLToXML(x) # wbxml to xml decoder

    def __init__(self, url, user, pwd, device_id):
        self.url       = url
        self.user      = user
        self.password  = pwd
        self.device_id = device_id

    def _create_connection(self, *args, **kwargs):
        self.connection = Connection.create(self.url, self.user, self.password, *args, **kwargs)

    def _encode(self, content):
        print "\n==Request==\n",content,"\n"
        return self.encoder(content)
#        return self.encoder(libxml2.parseDoc(content))

    def _decode(self, content):
#        return self.decoder(content)
        print "\n==Response==\n",str(self.decoder(content)),"\n"
#        print "\n==Response==\n",tostring(fromstring(str(self.decoder(content)))),"\n"
        return fromstring(str(self.decoder(content)))#Trick to use ElementTree instead of libxml2 in waiting for own ElementTree parser

    def _send(self, encoded_content, *args, **kwargs):
        try:
            return self.connection.send(self.command, encoded_content, self.device_id, *args, **kwargs)
        except restkit.errors.Unauthorized:
            raise CremeActiveSyncError(SYNC_ERR_FORBIDDEN)

    def send(self, template_dict, *args, **kwargs):
        content = render_to_string(self.template_name, template_dict)
#        print "xml sended :\n", content,"\n\n"
        encoded_content = self._encode(content)
        response = self._send(encoded_content, *args, **kwargs)
#        print "wbxml received:\n", response,"\n\n"
        return self._decode(response)