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
from django.db.models.signals import post_delete

from creme_core.models.relation import Relation

from activities.models.activity import Calendar

from constants import REL_SUB_PART_2_ACTIVITY, REL_OBJ_PART_2_ACTIVITY

def set_null_calendar_on_delete_participant(sender, instance, **kwargs):
    contact = None
    if instance.type_id == REL_SUB_PART_2_ACTIVITY:
        contact  = instance.subject_entity.get_real_entity()
        activity = instance.object_entity.get_real_entity()

    if instance.type_id == REL_OBJ_PART_2_ACTIVITY:
        contact  = instance.object_entity.get_real_entity()
        activity = instance.subject_entity.get_real_entity()

    if contact and contact.is_user:
        activity.calendars.remove(Calendar.get_user_default_calendar(contact.is_user))


def connect_to_signals():
    post_delete.connect(set_null_calendar_on_delete_participant, sender=Relation)
