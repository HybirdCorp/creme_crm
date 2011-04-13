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

from django.utils.translation import ugettext as _

################################################################################
# Creme active sync constants
SYNC_ERR_FORBIDDEN               = -1
SYNC_ERR_WRONG_CFG_NO_SERVER_URL = 0
SYNC_ERR_WRONG_CFG_NO_LOGIN      = 1
SYNC_ERR_WRONG_CFG_NO_PWD        = 2
SYNC_ERR_ABORTED                 = 3
SYNC_ERR_CONNECTION              = 4
SYNC_ERR_NOT_FOUND               = 5

SYNC_ERR_CREME_PERMISSION_DENIED_CREATE          =  6
SYNC_ERR_CREME_PERMISSION_DENIED_CREATE_SPECIFIC =  7
SYNC_ERR_CREME_PERMISSION_DENIED_CHANGE          =  8
SYNC_ERR_CREME_PERMISSION_DENIED_CHANGE_SPECIFIC =  9
SYNC_ERR_CREME_PERMISSION_DENIED_DELETE          = 10
SYNC_ERR_CREME_PERMISSION_DENIED_DELETE_SPECIFIC = 11

SYNC_ERR_VERBOSE = {
    SYNC_ERR_FORBIDDEN:               _(u"Wrong username and/or password"),
    SYNC_ERR_WRONG_CFG_NO_SERVER_URL: _(u"No server url, please fill in information in global settings configuration or in your own settings"),
    SYNC_ERR_WRONG_CFG_NO_LOGIN:      _(u"No login, please fill in information in your own settings"),
    SYNC_ERR_WRONG_CFG_NO_PWD:        _(u"No password, please fill in information in your own settings"),
    SYNC_ERR_ABORTED:                 _(u"There was an error during synchronization"),
    SYNC_ERR_CONNECTION:              _(u"It seems there no available connection"),
    SYNC_ERR_NOT_FOUND:               _(u"Wrong configuration (wrong server url?)"),
    
    SYNC_ERR_CREME_PERMISSION_DENIED_CREATE:          _(u"You haven't the right to create contacts in Creme"),
    SYNC_ERR_CREME_PERMISSION_DENIED_CREATE_SPECIFIC: _(u"You haven't the right to create contact <%s> in Creme"),#Useful?
    SYNC_ERR_CREME_PERMISSION_DENIED_CHANGE:          _(u"You haven't the right to change contacts in Creme"),
    SYNC_ERR_CREME_PERMISSION_DENIED_CHANGE_SPECIFIC: _(u"You haven't the right to change the contact <%s> in Creme"),
    SYNC_ERR_CREME_PERMISSION_DENIED_DELETE:          _(u"You haven't the right to delete contacts in Creme"),
    SYNC_ERR_CREME_PERMISSION_DENIED_DELETE_SPECIFIC: _(u"You haven't the right to delete the contact <%s> in Creme"),
}

class CremeActiveSyncError(Exception):
    def __init__(self, msg):
        super(CremeActiveSyncError, self).__init__(SYNC_ERR_VERBOSE.get(msg, msg))