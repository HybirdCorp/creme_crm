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
from restkit import Resource, BasicAuth
from wbxml.converters import XMLToWBXML, WBXMLToXML

class Connection(Resource):
    def __init__(self,  url, pool_instance=None, **kwargs):
        super(Connection, self).__init__(url, follow_redirect=True,
                                        max_follow_redirect=10,
                                        pool_instance=pool_instance,
                                        **kwargs)

#    def post(self, path=None, payload=None, headers=None, cmd="", device_id=None, **params):
#        self.uri += "?Cmd=%s&DeviceId=%s&DeviceType=SmartPhone" % (cmd, device_id)
    def post(self, path=None, payload=None, headers=None, cmd="", device_id=None, device_type="SmartPhone", **params):
        min_headers = {
            "Ms-Asprotocolversion": "2.5",
        #            "X-Ms-Policykey": "1286668650",
            "User-Agent": "MSFT-PPC/5.2.200",
            "Connection": "close",
            "Content-Type": "application/vnd.ms-sync.wbxml",
        }

        if headers:
            min_headers.update(headers)

        return super(Connection, self).post(path=path, payload=payload, headers=min_headers, Cmd=cmd, DeviceId=device_id, DeviceType=device_type, **params)
#        return super(Connection, self).post(path=path, payload=payload, headers=min_headers, **params)

#    def request(self, method, path=None, payload=None, headers=None, **params):

    @staticmethod
    def create(url, user, pwd, *args, **kwargs):
        filters = [BasicAuth(user, pwd)]
        try:
            _filters = kwargs.pop('filters')
            filters.extend(_filters)
        except KeyError:
            pass

        return Connection(url, filters=filters, *args, **kwargs)

    def send(self, cmd, content, device_id, *args, **kwargs):
        return self.post(cmd=cmd, payload=content, device_id=device_id, *args, **kwargs).body_string()

def request(url, user, pwd, cmd, content):
    return Connection.create(url, user, pwd).send(cmd, content)

def request_xml(url, device_id, user, pwd, cmd, str_xml):
    return WBXMLToXML(Connection.create(url, user, pwd).send(cmd, XMLToWBXML(libxml2.parseDoc(str_xml)), device_id))

if __name__ == "__main__":
    try:
#        fsync22m = """<?xml version="1.0" encoding="utf-8"?><FolderSync xmlns="FolderHierarchy:"><SyncKey>0</SyncKey></FolderSync>"""
#        print request_xml("http://127.0.0.1/Microsoft-Server-ActiveSync", "A9E11CADF9DF5120CE1558BF5CB22B70", "raph", "raph", "FolderSync", fsync22m)
        from constants import SYNC_PROVISION_RWSTATUS_NA

        provision = """<?xml version="1.0" encoding="utf-8"?><Provision xmlns="Provision:"><RemoteWipe><Status>%s</Status></RemoteWipe></Provision>""" % SYNC_PROVISION_RWSTATUS_NA

        r=Connection.create("http://127.0.0.1/Microsoft-Server-ActiveSync", "raph", "raph").send("Provision", XMLToWBXML(libxml2.parseDoc(provision)), "A9E11CADF9DF5120CE1558BF5CB22B70")
#        r=Connection.create("https://m.hotmail.com", "aquaplanning2010@hotmail.fr", "aquaplanning").send("Provision", XMLToWBXML(libxml2.parseDoc(provision)), "A9E11CADF9DF5120CE1558BF5CB22B70")
#        r=Connection.create("http://m.google.com", "leozleoz01@gmail.com", "azeqsdwxc").send("Provision", XMLToWBXML(libxml2.parseDoc(provision)), "A9E11CADF9DF5120CE1558BF5CB22B70")
        print WBXMLToXML(r)
#        print request_xml("http://127.0.0.1/Microsoft-Server-ActiveSync", "A9E11CADF9DF5120CE1558BF5CB22B70", "raph", "raph", "Provision", provision)
    except Exception, e:
        if hasattr(e, 'response'):
            print "Error. Response from server :", e.response.status
        else:
            print "Error. Response from server :", e
            
#    print request_xml("http://127.0.0.1/Microsoft-Server-ActiveSync", "BAD73E6E02156460E800185977C03182", "raph", "raph", "FolderSync", fsync22m)

