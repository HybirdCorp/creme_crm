################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

import collections
import logging
from datetime import datetime, timedelta

from django.db.models import Q, QuerySet
from django.utils.timezone import (
    get_current_timezone,
    localtime,
    now,
    zoneinfo,
)
from django.utils.translation import gettext as _

from creme.creme_core.models import Relation, SettingValue
from creme.creme_core.utils.dates import to_utc

from . import get_activity_model
# from .constants import FLOATING_TIME, NARROW
from .constants import REL_SUB_PART_2_ACTIVITY
from .setting_keys import auto_subjects_key

logger = logging.getLogger(__name__)


def get_last_day_of_a_month(date):
    for day in (31, 30, 29, 28):
        try:
            last_day = date.replace(day=day)
        except ValueError:
            pass
        else:
            break

    return last_day


def get_current_utc_offset():
    tz = get_current_timezone()
    return int(tz.utcoffset(now()).total_seconds() / 60)


def check_activity_collisions(
        activity_start,
        activity_end,
        participants,
        busy=True,
        exclude_activity_id=None):
    if not activity_start:
        return

    collision_test = ~(Q(end__lte=activity_start) | Q(start__gte=activity_end))
    collisions = []

    for participant in participants:
        # Find activities of participant
        activity_req = Relation.objects.filter(
            subject_entity=participant.id, type=REL_SUB_PART_2_ACTIVITY,
        )

        # Exclude current activity if asked
        if exclude_activity_id is not None:
            activity_req = activity_req.exclude(object_entity=exclude_activity_id)

        # Get id of activities of participant
        activity_ids = activity_req.values_list('object_entity__id', flat=True)

        # Do collision request
        # TODO: can be done with less queries ?
        #           Activity.objects.filter(
        #               relations__object_entity=participant.id,
        #               relations__object_entity__type=REL_OBJ_PART_2_ACTIVITY,
        #           ).filter(collision_test)
        busy_args = {} if busy else {'busy': True}
        # TODO: test is_deleted=True
        Activity = get_activity_model()
        colliding_activity = Activity.objects.filter(
            collision_test,
            is_deleted=False,
            pk__in=activity_ids,
            floating_type__in=(
                Activity.FloatingType.NARROW,
                Activity.FloatingType.FLOATING_TIME,
            ),
            **busy_args
        ).first()

        if colliding_activity is not None:
            collision_start = max(
                activity_start.time(), localtime(colliding_activity.start).time(),
            )
            collision_end = min(
                activity_end.time(), localtime(colliding_activity.end).time(),
            )

            collisions.append(
                _(
                    '{participant} already participates in the activity '
                    '«{activity}» between {start} and {end}.'
                ).format(
                    participant=participant,
                    activity=colliding_activity,
                    start=collision_start,
                    end=collision_end,
                )
            )

    return collisions


def is_auto_orga_subject_enabled():
    return SettingValue.objects.get_4_key(auto_subjects_key, default=False).value


class ICalEncoder:
    """Generates RFC5545 iCalendar files (extension .ics).
    See https://www.rfc-editor.org/rfc/rfc5545
    """
    prefetched_fields = ['type', 'sub_type', 'status']

    # <PRODID>
    product_editor = 'hybird.org'
    product_label = 'CremeCRM'  # TODO: settings.SOFTWARE_LABEL ?
    product_language = 'EN'

    def __init__(self):
        self.now = now()

    @staticmethod
    def format_utc_datetime(date_time) -> str:
        utc = to_utc(date_time)

        return (
            f'{utc.year}{utc.month:02}{utc.day:02}'
            f'T{utc.hour:02}{utc.minute:02}{utc.second:02}Z'
        )

    @staticmethod
    def format_local_datetime(date_time, tz) -> str:
        local = date_time.astimezone(tz)

        return (
            f'{local.year}{local.month:02}{local.day:02}'
            f'T{local.hour:02}{local.minute:02}{local.second:02}'
        )

    @property
    def product_id(self):
        from creme import __version__ as version
        return f'-//{self.product_editor}//{self.product_label} {version}//{self.product_language}'

    def encode_activity(self, activity, tz) -> str:
        # TODO: <LOCATION;LANGUAGE=en:Germany> ?
        # LAST-MODIFIED is equivalent to DTSTAMP because there is no METHOD
        return f"""BEGIN:VEVENT
UID:{activity.uuid}
DTSTAMP:{self.format_utc_datetime(self.now)}
SUMMARY:{activity.title}
DTSTART;TZID={tz}:{self.format_local_datetime(activity.start, tz)}
DTEND;TZID={tz}:{self.format_local_datetime(activity.end, tz)}
LOCATION:{activity.place}
CATEGORIES:{activity.type.name},{activity.sub_type.name}
STATUS:{activity.status or ''}
END:VEVENT"""

    def encode(self, activities: QuerySet) -> str:
        """Return a normalized iCalendar string."""
        tz = get_current_timezone()
        activities = activities.prefetch_related(*self.prefetched_fields)
        start_year = min(
            (a.start.date().year for a in activities if a.start),
            default=2000,
        )
        end_year = max(
            (a.end.date().year for a in activities if a.end),
            default=start_year + 10,
        )

        return """BEGIN:VCALENDAR
VERSION:2.0
PRODID:{product_id}
CALSCALE:GREGORIAN
{vtimezone}
{vevents}
END:VCALENDAR""".format(
            product_id=self.product_id,
            vtimezone=ZoneinfoToVtimezone.generate_vtimezone(
                timezone=tz,
                date_from=datetime(year=start_year, month=1, day=1),
                date_to=datetime(year=end_year, month=12, day=31),
            ),
            vevents='\n'.join(self.encode_activity(a, tz) for a in activities),
        )


################################################################################
# PUBLIC DOMAIN
#
# Heavily modified version of this snippet by ariannedee:
#    https://gist.github.com/ariannedee/582c1e6d355f34bad994011ec4b267d8
# which was itself based on this snippet by Claus Fischer (claus.fischer@clausfischer.com)
#    https://www.djangosnippets.org/snippets/10569/
# Thanks to them <3
#
# Modifications: default values removed, f-strings, class-methods, renaming...
################################################################################

# The VTIMEZONE essentially consists of a timezone id TZID that can be
# referenced by timestamps outside the timezone information, and of multiple
# sub-parts named STANDARD or DAYLIGHT.
#
# It seems that there is no functional distinction between using the STANDARD
# or DAYLIGHT subsection name, and that there are two different names used
# just for convenience and human readability. The different functionality of
# STANDARD and DAYLIGHT parts, if present in a VTIMEZONE, comes solely from
# the TZOFFSETTO and TZNAME properties.
#
# The VTIMEZONE part must contain at least one STANDARD or DAYLIGHT part and
# may contain more.
#
# Henceforth, I will call a STANDARD/DAYLIGHT part just a 'part'.
#
# Each part consists of:
#
# TZOFFSETFROM An UTC offset 'before' the onset of this part. It is present to
#     serve as a basis for timestamps used in the definition of the part.
#
#     All timestamps in a part (DTSTART, RDATE, and all timestamps in RRULE
#     except for UNTIL if UNTIL is present in RRULE) are local times based on
#     TZOFFSETFROM, i.e. they are used on the UTC offset before the part
#     starts to be effective.
#
# TZOFFSETTO An UTC offset to apply to all timestamps used outside the
#     VTIMEZONE definition that use this timezone as a basis.
#
# DTSTART The first start of effect of this part, i.e. the start of the first
#     time interval during which this part determines the UTC offset.
#     Based on UTC plus TZOFFSETTO.
#
# RDATE A repeated occurrence of start-of-effect of this part after DTSTART,
#     i.e. the start of another interval.
#     This parameter is optional but may be given multiple times.
#     Its purpose is to keep the VTIMEZONE segment compact.
#     Based on UTC plus TZOFFSETTO.
#
# RRULE Not used in this implementation.
#       The RRULE offers an alternative, more compact and open-ended way of
#       defining the intervals when this part is effective.
#
# TZNAME Name of timezone during the effectiveness of this part, for outside use.
#
# Note on RRULE:
#
# Calendar programs often have access to good structured timezone information
# that defines the onset of daylight saving time or standard time by recurring
# rules (RRULE in the RFC).
#
# I do not know whether pytz has this information in a way that can be
# consistently converted to RRULEs for the VTIMEZONE's STANDARD or DAYLIGHT
# sub-parts.
#
# Therefore, this implementation does not make use of RRULE.
#
# Instead, since the requirement for this implementation is just to cover the
# specified date range, using multiple STANDARD and DAYLIGHT sub-parts will do.
# If they share the essential properties, they can be combined by using RDATE.
#
# NB: search DST transitions through the zoneinfo API ; probably not efficient at
# all, & we could use the files used by zoneinfo to find the data we want...
class ZoneinfoToVtimezone:
    """Generates RFC5545 compatible VTIMEZONE information for iCalendar files."""
    Part = collections.namedtuple(
        'Part',
        [
            'is_daylight',   # DAYLIGHT or STANDARD
            'tzoffsetfrom',  # timedelta
            'tzoffsetto',    # timedelta
            'dtstart',       # datetime
            'rdatelist',     # list of rdate values
            'tzname',        # name string
        ],
    )

    @classmethod
    def _generate_parts(cls,
                        timezone,
                        date_from: datetime,
                        date_to: datetime,
                        ) -> list[Part] | None:
        """Auxiliary function to assemble the raw data of the parts.
        Returns None on failure.
        """
        # Check range consistency
        if date_from > date_to:
            return None

        # TODO: cache the utcoffset() which are recomputed several times?
        # Find the transition between 2 'datetimes' with a recursive bisection
        def bisect_transition(d1, d2) -> ZoneinfoToVtimezone.Part | None:
            offset1 = timezone.utcoffset(d1)
            offset2 = timezone.utcoffset(d2)

            if offset1 == offset2:
                return None

            delta = (d2 - d1) / 2

            # This part may be totally bullshit (seems to give same results
            # than pour pytz code). A transition could be at minutes=30 ?
            if delta < timedelta(minutes=30):
                return cls.Part(
                    is_daylight=bool(timezone.dst(d2)),
                    tzoffsetfrom=offset1,
                    tzoffsetto=offset2,
                    dtstart=(d1 if offset1 < offset2 else d2).replace(
                        minute=0, second=0, microsecond=0,
                    ),
                    rdatelist=[],
                    tzname=timezone.tzname(d2),
                )

            d3 = d1 + delta

            return (
                bisect_transition(d3, d2)
                if timezone.utcoffset(d3) == offset1 else
                bisect_transition(d1, d3)
            )

        # Generate pairs of datetimes representing consecutive month (in the past)
        def forward_month_ranges(start):
            while True:
                end = start + timedelta(days=30)
                yield start, end
                start = end

        # Generate pairs of datetimes representing consecutive month (in the future)
        def backward_month_ranges(start):
            while True:
                end = start - timedelta(days=30)
                yield end, start
                start = end

        def yield_transition(months):
            for month_start, month_end in months:
                part = bisect_transition(month_start, month_end)
                if part:
                    yield part

        # We add the transition which is before "date_from".
        parts = [next(yield_transition(backward_month_ranges(date_from)))]

        # We add all the transition which cover the range [date_from, date_to]
        for part in yield_transition(forward_month_ranges(date_from)):
            if part.dtstart > date_to:
                break

            parts.append(part)

        # Now merge parts that are almost equal
        merged_parts = []
        previous_part = [None, None]  # non-dst and dst

        for part in parts:
            # While the Part itself is immutable, its rdatelist can be appended to.
            is_daylight = part.is_daylight
            ppart = previous_part[is_daylight]

            if ppart is None:
                previous_part[is_daylight] = part
                merged_parts.append(part)
            else:
                if (
                    ppart.is_daylight == part.is_daylight
                    and ppart.tzoffsetfrom == part.tzoffsetfrom
                    and ppart.tzname == part.tzname
                    and ppart.tzoffsetto == part.tzoffsetto
                ):
                    # Merge the parts
                    ppart.rdatelist.append(part.dtstart)
                else:
                    # Start a new history
                    previous_part[is_daylight] = part
                    merged_parts.append(part)

        return merged_parts

    @classmethod
    def _offset_as_str(cls, offset):
        seconds = offset.seconds
        hours, remainder = divmod(abs(seconds), 3600)

        return '{sign}{hours:02d}{minutes:02d}'.format(
            sign='+' if seconds > 0 else '-',
            hours=hours,
            minutes=remainder // 60,
        )

    @classmethod
    def generate_vtimezone(cls,
                           timezone: zoneinfo.ZoneInfo,
                           date_from: datetime,
                           date_to: datetime,
                           ) -> str:
        """Generate VTIMEZONE as a string."""
        parts = cls._generate_parts(timezone, date_from, date_to)
        if not parts:
            logger.warning('The VTIMEZONE cannot be generated.')
            return ''

        lines = ['BEGIN:VTIMEZONE', f'TZID:{timezone.key}']

        for part in parts:
            part_name = 'DAYLIGHT' if part.is_daylight else 'STANDARD'

            lines.append(f'BEGIN:{part_name}')
            lines.append(f'TZOFFSETFROM:{cls._offset_as_str(part.tzoffsetfrom)}')
            lines.append(f'TZOFFSETTO:{cls._offset_as_str(part.tzoffsetto)}')
            lines.append(part.dtstart.strftime('DTSTART:%Y%m%dT%S%H%M'))
            lines.extend(
                rdate.strftime('RDATE:%Y%m%dT%S%H%M') for rdate in part.rdatelist
            )
            lines.append(f'TZNAME:{part.tzname}')
            lines.append(f'END:{part_name}')

        lines.append('END:VTIMEZONE')

        # '\r\n' is standard, '\n' is better
        return '\n'.join(lines)
