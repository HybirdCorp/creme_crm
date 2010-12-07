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

from activesync.sync import Synchronization
from activesync.config    import *
from activesync.commands  import *
from activesync.constants import *

from restkit.errors import (ResourceNotFound, Unauthorized, RequestFailed,
                            ParserError, RequestError)

#Advised order
#Provision
#FolderSync
#GetItemEstimate
#Sync
#Sync
#Ping

def main():
#    try:
    sync = Synchronization(User.objects.get(pk=1))
    sync.synchronize()
#    except (ResourceNotFound, Unauthorized, RequestFailed, ParserError, RequestError), e:
#        print "Error. Response from server :", e.response.status


def main0():
    try:
        params = (SERVER_URL, USER, PWD, CLIENT_ID)
        p = Provision(*params)
        p.send()
        policy_key = p.policy_key

        fs = FolderSync(*params)
        fs.send(policy_key)

        contacts = filter(lambda x: int(x['type']) == SYNC_FOLDER_TYPE_CONTACT, fs.add)

        if contacts:
            contact_folder = contacts[0]

            serverid = contact_folder.get('serverid')

            as_ = AirSync(*params)
            as_.send(policy_key, serverid, None)#fs.synckey)

#            from time import sleep
#            sleep(3)
#            as_2 = AirSync(*params)
#            as_2.send(policy_key, serverid, as_.last_synckey)


    except (ResourceNotFound, Unauthorized, RequestFailed, ParserError, RequestError), e:
        print "Error. Response from server :", e.response.status

#    except Exception, e:
#            print "Exception :", e