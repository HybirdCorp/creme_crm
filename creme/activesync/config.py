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

#SERVER_URL = "http://127.0.0.1/Microsoft-Server-ActiveSync"
#USER = "raph"
#PWD  = "raph"
#CLIENT_ID = "64F55E2D0EE7A12E717863BA8048BED1"

#TODO: Delete this
IS_ZPUSH = True
#IS_ZPUSH = False

CONFLICT_MODE = 1 #0 Client object replaces server object. / 1 Server object replaces client object.

ACTIVE_SYNC_DEBUG = True #Make appears some debug informations on the UI

LIMIT_SYNC_KEY_HISTORY = 50 #Number of sync_keys kept in db by user

CONNECTION_TIMEOUT = 150

PICTURE_LIMIT_SIZE = 55000 #E.g: 55Ko Active sync servers don't handle pictures > to this size
