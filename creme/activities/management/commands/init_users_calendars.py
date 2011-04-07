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

from django.core.management.base import BaseCommand
from django.contrib.auth.models  import User
from django.db.models import Q
from django.db.utils import IntegrityError

from creme.persons.models.contact import Contact

from activities.models.activity import Calendar, Activity
from activities.constants import REL_OBJ_ACTIVITY_SUBJECT, REL_OBJ_PART_2_ACTIVITY#, REL_OBJ_LINKED_2_ACTIVITY

class Command(BaseCommand):
    help = 'Create user defaults calendars and link them to unlinked activities.'
    args = ''

    def handle(self, *args, **options):
        contacts_get                  = Contact.objects.get
        activities_filter             = Activity.objects.filter
        calendar_get_default_calendar = Calendar.get_user_default_calendar

        for user in User.objects.all():
            user_calendar = calendar_get_default_calendar(user)#Create if doesn't exist

            try:
                user_contact_file = contacts_get(is_user=user)
            except Contact.DoesNotExist:
                user_contact_file = None

            q_filter  = Q(user=user)
            q_filter |= Q(relations__type=REL_OBJ_ACTIVITY_SUBJECT,  relations__object_entity=user_contact_file)
            q_filter |= Q(relations__type=REL_OBJ_PART_2_ACTIVITY,   relations__object_entity=user_contact_file)
            
            #In the current actvity creation process it doesn't link activity to
            #an user calendar for the REL_OBJ_LINKED_2_ACTIVITY relation
#            q_filter |= Q(relations__type=REL_OBJ_LINKED_2_ACTIVITY, relations__object_entity=user_contact_file)
            
            for activity in activities_filter(q_filter).distinct():
                try:
                    activity.calendars.add(user_calendar)
                    print "Link %s (pk=%s) to calendar : %s" % (activity, activity.pk, user_calendar)
                except IntegrityError:
                    pass


