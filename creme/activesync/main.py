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
#    sync = Synchronization(User.objects.get(pk=1))
#    sync = Synchronization(User.objects.get(pk=2))
    sync = Synchronization(User.objects.get(pk=3))
    sync.synchronize()
#    except (ResourceNotFound, Unauthorized, RequestFailed, ParserError, RequestError), e:
#        print "Error. Response from server :", e.response.status

