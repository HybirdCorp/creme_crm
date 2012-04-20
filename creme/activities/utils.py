# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from datetime import timedelta

from django.db.models.query_utils import Q
from django.utils.translation import ugettext

from creme_core.models.relation import Relation

from activities.constants import REL_SUB_PART_2_ACTIVITY


def get_last_day_of_a_month(date):
    rdate = date.replace(day=1)
    try:
        rdate = rdate + timedelta(days=31)
    except:
        try:
            rdate = rdate + timedelta(days=30)
        except :
            try :
                rdate = rdate + timedelta(days=29)
            except:
                rdate = rdate + timedelta(days=28)
    return rdate


def check_activity_collisions(activity_start, activity_end, participants, busy=True, exclude_activity_id=None):
    from activities.models.activity import Activity

    collision_test = ~(Q(end__lte=activity_start) | Q(start__gte=activity_end))
    collisions     = []

    for participant in participants:
        # find activities of participant
        activity_req = Relation.objects.filter(subject_entity=participant.id, type=REL_SUB_PART_2_ACTIVITY)

        # exclude current activity if asked
        if exclude_activity_id is not None:
            activity_req = activity_req.exclude(object_entity=exclude_activity_id)

        # get id of activities of participant
        activity_ids = activity_req.values_list("object_entity__id", flat=True)

        # do collision request
        #TODO: can be done with less queries ?
        #  eg:  Activity.objects.filter(relations__object_entity=participant.id, relations__object_entity__type=REL_OBJ_PART_2_ACTIVITY).filter(collision_test)
        #activity_collisions = Activity.objects.exclude(busy=False).filter(pk__in=activity_ids).filter(collision_test)[:1]
        #activity_collisions = Activity.objects.filter(pk__in=activity_ids).filter(collision_test)[:1]
        busy_args = {} if busy else {'busy': True}
        activity_collisions = Activity.objects.filter(collision_test, **busy_args).filter(pk__in=activity_ids)[:1]

        if activity_collisions:
            collision = activity_collisions[0]
            collision_start = max(activity_start.time(), collision.start.time())
            collision_end   = min(activity_end.time(),   collision.end.time())

            collisions.append(ugettext(u"%(participant)s already participates to the activity «%(activity)s» between %(start)s and %(end)s.") % {
                        'participant': participant,
                        'activity':    collision,
                        'start':       collision_start,
                        'end':         collision_end,
                    })

    return collisions

def get_ical_date(dateTime):
    return "%(year)s%(month)02d%(day)02dT%(hour)02d%(minute)02d%(second)02dZ" % {
        'year' : dateTime.year,
        'month': dateTime.month,
        'day'  : dateTime.day,
        'hour'  : dateTime.hour,
        'minute'  : dateTime.minute,
        'second'  : dateTime.second
    }

def get_ical(activities):
    """Return a normalized iCalendar string
    /!\ Each parameter has to be separated by \n ONLY no spaces allowed!
    Example : BEGIN:VCALENDAR\nVERSION:2.0"""
    return """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//CremeCRM//CremeCRM//EN
%s
END:VCALENDAR"""  % "".join(a.as_ical_event() for a in activities)
