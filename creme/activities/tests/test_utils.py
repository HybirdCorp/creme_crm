from datetime import date
from functools import partial

import pytz
from django.utils.timezone import get_current_timezone
from django.utils.timezone import override as override_tz
from django.utils.translation import pgettext

from creme import __version__ as creme_version

from .. import constants
from ..utils import ICalEncoder, PytzToVtimezone
from .base import Activity, _ActivitiesTestCase, skipIfCustomActivity


@skipIfCustomActivity
class ICalEncoderTestCase(_ActivitiesTestCase):
    @override_tz('Europe/Paris')
    def test_encode_activity01(self):
        user = self.create_user()
        create_dt = self.create_datetime

        activity = Activity.objects.create(
            user=user,
            title='Act#1',
            # busy=True,  # TODO ?
            type_id=constants.ACTIVITYTYPE_MEETING,
            sub_type_id=constants.ACTIVITYSUBTYPE_MEETING_MEETING,
            start=create_dt(year=2023, month=1, day=17, hour=9),
            end=create_dt(year=2023, month=1, day=17, hour=10),
        )

        encoder = ICalEncoder()
        encoder.now = create_dt(year=2023, month=1, day=17, hour=17, minute=28)

        self.assertEqual(
            f'BEGIN:VEVENT\n'
            f'UID:{activity.uuid}\n'
            f'DTSTAMP:20230117T162800Z\n'
            f'SUMMARY:{activity.title}\n'
            f'DTSTART;TZID=Europe/Paris:20230117T090000\n'
            f'DTEND;TZID=Europe/Paris:20230117T100000\n'
            f'LOCATION:\n'
            f'CATEGORIES:{activity.type.name},{activity.sub_type.name}\n'
            f'STATUS:\n'
            f'END:VEVENT',
            encoder.encode_activity(activity, tz=get_current_timezone()),
        )

    @override_tz('Europe/London')
    def test_encode_activity02(self):
        user = self.create_user()
        create_dt = self.create_datetime

        activity = Activity.objects.create(
            user=user,
            title='My Activity',
            type_id=constants.ACTIVITYTYPE_PHONECALL,
            sub_type_id=constants.ACTIVITYSUBTYPE_PHONECALL_OUTGOING,
            start=create_dt(year=2023, month=3, day=26, hour=14, minute=30),
            end=create_dt(year=2023, month=3, day=26, hour=16),
            place='Tour Eiffel',
            status_id=constants.STATUS_PLANNED,
        )

        encoder = ICalEncoder()
        encoder.now = create_dt(year=2023, month=1, day=17, hour=17, minute=36)

        self.assertEqual(
            f'BEGIN:VEVENT\n'
            f'UID:{activity.uuid}\n'
            f'DTSTAMP:20230117T173600Z\n'
            f'SUMMARY:{activity.title}\n'
            f'DTSTART;TZID=Europe/London:20230326T143000\n'
            f'DTEND;TZID=Europe/London:20230326T160000\n'
            f'LOCATION:{activity.place}\n'
            f'CATEGORIES:{activity.type.name},{activity.sub_type.name}\n'
            f'STATUS:{pgettext("activities-status", "Planned")}\n'
            f'END:VEVENT',
            encoder.encode_activity(activity, tz=get_current_timezone()),
        )

    def test_PytzToVtimezone01(self):
        tz = pytz.timezone('Europe/Paris')
        self.assertEqual(
            """BEGIN:VTIMEZONE
TZID:Europe/Paris
BEGIN:STANDARD
TZOFFSETFROM:+0200
TZOFFSETTO:+0100
DTSTART:20091025T000300
RDATE:20101031T000300
TZNAME:CET
END:STANDARD
BEGIN:DAYLIGHT
TZOFFSETFROM:+0100
TZOFFSETTO:+0200
DTSTART:20100328T000200
TZNAME:CEST
END:DAYLIGHT
END:VTIMEZONE""",
            PytzToVtimezone.generate_vtimezone(
                pytz_timezone=tz,
                date_from=date(year=2010, month=1, day=1),
                date_to=date(year=2010, month=12, day=31),
            ),
        )
        self.assertEqual(
            """BEGIN:VTIMEZONE
TZID:Europe/Paris
BEGIN:STANDARD
TZOFFSETFROM:+0200
TZOFFSETTO:+0100
DTSTART:20091025T000300
RDATE:20101031T000300
RDATE:20111030T000300
TZNAME:CET
END:STANDARD
BEGIN:DAYLIGHT
TZOFFSETFROM:+0100
TZOFFSETTO:+0200
DTSTART:20100328T000200
RDATE:20110327T000200
TZNAME:CEST
END:DAYLIGHT
END:VTIMEZONE""",
            PytzToVtimezone.generate_vtimezone(
                pytz_timezone=tz,
                date_from=date(year=2010, month=1, day=1),
                date_to=date(year=2011, month=12, day=31),
            ),
        )

    def test_PytzToVtimezone02(self):
        tz = pytz.timezone('Europe/London')
        self.assertEqual(
            """BEGIN:VTIMEZONE
TZID:Europe/London
BEGIN:STANDARD
TZOFFSETFROM:+0100
TZOFFSETTO:-0000
DTSTART:20091025T000200
RDATE:20101031T000200
TZNAME:GMT
END:STANDARD
BEGIN:DAYLIGHT
TZOFFSETFROM:-0000
TZOFFSETTO:+0100
DTSTART:20100328T000100
TZNAME:BST
END:DAYLIGHT
END:VTIMEZONE""",
            PytzToVtimezone.generate_vtimezone(
                pytz_timezone=tz,
                date_from=date(year=2010, month=1, day=1),
                date_to=date(year=2010, month=12, day=31),
            ),
        )

    @override_tz('Europe/Paris')
    def test_encode(self):
        user = self.create_user()

        create_act = partial(
            Activity.objects.create,
            user=user, busy=True,
            type_id=constants.ACTIVITYTYPE_MEETING,
            sub_type_id=constants.ACTIVITYSUBTYPE_MEETING_MEETING,
        )
        create_dt = self.create_datetime
        act1 = create_act(
            title='Act#1',
            start=create_dt(year=2023, month=4, day=1, hour=9),
            end=create_dt(year=2023, month=4, day=1, hour=10),
        )
        act2 = create_act(
            title='Act#2',
            start=create_dt(year=2023, month=4, day=2, hour=9),
            end=create_dt(year=2023, month=4, day=2, hour=10),
        )

        content = ICalEncoder().encode(Activity.objects.filter(id__in=[act1.id, act2.id]))
        self.assertStartsWith(
            content,
            f'BEGIN:VCALENDAR\n'
            f'VERSION:2.0\n'
            f'PRODID:-//hybird.org//CremeCRM {creme_version}//EN\n'
            f'CALSCALE:GREGORIAN\n'
            f'BEGIN:VTIMEZONE\n'
            f'TZID:Europe/Paris\n'
            f'BEGIN:STANDARD\n'
            f'TZOFFSETFROM:+0200\n'
            f'TZOFFSETTO:+0100\n'
            f'DTSTART:20221030T000300\n'
            f'RDATE:20231029T000300\n'
            f'TZNAME:CET\n'
            f'END:STANDARD\n'
            f'BEGIN:DAYLIGHT\n'
            f'TZOFFSETFROM:+0100\n'
            f'TZOFFSETTO:+0200\n'
            f'DTSTART:20230326T000200\n'
            f'TZNAME:CEST\n'
            f'END:DAYLIGHT\n'
            f'END:VTIMEZONE\n'
            f'BEGIN:VEVENT\n'
            f'UID:{act2.uuid}\n'
        )
        self.assertIn(f'UID:{act1.uuid}\n', content)
        self.assertCountOccurrences('UID:', content, 2)
        self.assertEndsWith(content, 'END:VEVENT\nEND:VCALENDAR')
