# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from django.db.models.query_utils import Q
from django.utils.timezone import localtime
from django.utils.translation import ugettext as _

from creme.creme_core.models import Relation

from . import get_activity_model
from .constants import REL_SUB_PART_2_ACTIVITY, NARROW, FLOATING_TIME


def get_last_day_of_a_month(date):
    for day in (31, 30, 29, 28):
        try:
            last_day = date.replace(day=day)
        except ValueError:
            pass
        else:
            break

    return last_day


def check_activity_collisions(activity_start, activity_end, participants, busy=True, exclude_activity_id=None):
    if not activity_start:
        return

    collision_test = ~(Q(end__lte=activity_start) | Q(start__gte=activity_end))
    collisions     = []

    for participant in participants:
        # Find activities of participant
        activity_req = Relation.objects.filter(subject_entity=participant.id, type=REL_SUB_PART_2_ACTIVITY)

        # Exclude current activity if asked
        if exclude_activity_id is not None:
            activity_req = activity_req.exclude(object_entity=exclude_activity_id)

        # Get id of activities of participant
        activity_ids = activity_req.values_list("object_entity__id", flat=True)

        # Do collision request
        # TODO: can be done with less queries ?
        #       eg:  Activity.objects.filter(relations__object_entity=participant.id,
        #                                    relations__object_entity__type=REL_OBJ_PART_2_ACTIVITY)
        #                            .filter(collision_test)
        busy_args = {} if busy else {'busy': True}
        # TODO: test is_deleted=True
        colliding_activity = get_activity_model().objects.filter(collision_test,
                                                                 is_deleted=False,
                                                                 pk__in=activity_ids,
                                                                 floating_type__in=(NARROW, FLOATING_TIME),
                                                                 **busy_args
                                                                ).first()

        if colliding_activity is not None:
            collision_start = max(activity_start.time(), localtime(colliding_activity.start).time())
            collision_end   = min(activity_end.time(),   localtime(colliding_activity.end).time())

            collisions.append(_(u"{participant} already participates to the activity "
                                u"«{activity}» between {start} and {end}."
                               ).format(
                        participant=participant,
                        activity=colliding_activity,
                        start=collision_start,
                        end=collision_end,
            ))

    return collisions


def get_ical_date(date_time):
    date_time = localtime(date_time)

    return '{year}{month:02}{day:02}T{hour:02}{minute:02}{second:02}Z'.format(
        year=date_time.year,
        month=date_time.month,
        day=date_time.day,
        hour=date_time.hour,
        minute=date_time.minute,
        second=date_time.second,
    )


def get_ical(activities):
    """Return a normalized iCalendar string
    /!\ Each parameter has to be separated by \n ONLY no spaces allowed!
    Example : BEGIN:VCALENDAR\nVERSION:2.0
    """
    return u"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//CremeCRM//CremeCRM//EN
{}
END:VCALENDAR""".format(''.join(a.as_ical_event() for a in activities))
