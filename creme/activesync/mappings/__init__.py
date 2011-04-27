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

from activities.models import Meeting, Task

from persons.models import Contact

from activesync.constants import SYNC_FOLDER_TYPE_CONTACT, SYNC_FOLDER_TYPE_APPOINTMENT, SYNC_FOLDER_TYPE_TASK
from activesync.mappings.contact import CREME_CONTACT_MAPPING, save_contact, update_contact, serialize_contact
from activesync.mappings.activity import CREME_MEETING_MAPPING, save_meeting, update_meeting
from activesync.mappings.utils import serialize_entity
#Mapping between AS folder types and creme types
FOLDERS_TYPES_CREME_TYPES_MAPPING = {
    SYNC_FOLDER_TYPE_CONTACT: Contact,
    SYNC_FOLDER_TYPE_APPOINTMENT: Meeting,
    SYNC_FOLDER_TYPE_TASK: Task,
}

CREME_TYPES_FOLDERS_TYPES_MAPPING = dict((v,k) for k, v in FOLDERS_TYPES_CREME_TYPES_MAPPING.iteritems())

##Mapping between Creme types and AS Classes
#AS_CLASSES = {
#    Contact: "Contacts",
#    Task: "Tasks",
##    :"Email",
#    Meeting: "Calendar",
##    :"SMS",
#}

CREME_AS_MAPPING = {
    Contact:{
        'mapping': CREME_CONTACT_MAPPING,
        'class': "Contacts",
        'save': save_contact,
        'update': update_contact,
#        'serializer': serialize_contact,
        'serializer': serialize_entity,
        'type': SYNC_FOLDER_TYPE_CONTACT,
    },
    Meeting:{
        'mapping': CREME_MEETING_MAPPING,
        'class': "Calendar",
        'save': save_meeting,
        'update': update_meeting,
        'serializer': serialize_entity,
        'type': SYNC_FOLDER_TYPE_APPOINTMENT,
    }
}