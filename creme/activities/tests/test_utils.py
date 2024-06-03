from datetime import date, datetime
from functools import partial

from django.core.exceptions import ValidationError
from django.utils.timezone import get_current_timezone
from django.utils.timezone import override as override_tz
from django.utils.timezone import zoneinfo
from django.utils.translation import pgettext

from creme import __version__ as creme_version
from creme.creme_core.models import Relation
from creme.persons.tests.base import skipIfCustomContact

from .. import constants
from ..models import Status
from ..utils import (
    ICalEncoder,
    ZoneinfoToVtimezone,
    check_activity_collisions,
    get_last_day_of_a_month,
)
from .base import Activity, Contact, _ActivitiesTestCase, skipIfCustomActivity


class UtilsTestCase(_ActivitiesTestCase):
    def test_get_last_day_of_a_month(self):
        self.assertEqual(
            date(year=2016, month=1, day=31),
            get_last_day_of_a_month(date(year=2016, month=1, day=1)),
        )
        self.assertEqual(
            date(year=2016, month=1, day=31),
            get_last_day_of_a_month(date(year=2016, month=1, day=18)),
        )

        # Other 31 days
        self.assertEqual(
            date(year=2016, month=3, day=31),
            get_last_day_of_a_month(date(year=2016, month=3, day=17)),
        )

        # 30 days
        self.assertEqual(
            date(year=2016, month=4, day=30),
            get_last_day_of_a_month(date(year=2016, month=4, day=17)),
        )
        self.assertEqual(
            date(year=2016, month=4, day=30),
            get_last_day_of_a_month(date(year=2016, month=4, day=30)),
        )

        # February
        self.assertEqual(
            date(year=2016, month=2, day=29),
            get_last_day_of_a_month(date(year=2016, month=2, day=17)),
        )
        self.assertEqual(
            date(year=2015, month=2, day=28),
            get_last_day_of_a_month(date(year=2015, month=2, day=17)),
        )

    def _check_activity_collisions(self,
                                   activity_start, activity_end,
                                   participants,
                                   busy=True, exclude_activity_id=None,
                                   ):
        collisions = check_activity_collisions(
            activity_start, activity_end, participants,
            busy=busy, exclude_activity_id=exclude_activity_id,
        )
        if collisions:
            raise ValidationError(collisions)

    @skipIfCustomContact
    def test_collision01(self):
        user = self.login_as_root_and_get()

        sub_type1 = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_MEETING)
        sub_type2 = self._get_sub_type(constants.UUID_SUBTYPE_PHONECALL_INCOMING)
        create_activity = partial(
            Activity.objects.create,
            user=user, type_id=sub_type1.type_id, sub_type=sub_type1,
        )
        create_dt = self.create_datetime

        with self.assertNoException():
            act01 = create_activity(
                title='call01',
                type_id=sub_type2.type_id, sub_type=sub_type2,
                start=create_dt(year=2010, month=10, day=1, hour=12, minute=0),
                end=create_dt(year=2010, month=10, day=1, hour=13, minute=0),
            )
            act02 = create_activity(
                title='meet01',
                start=create_dt(year=2010, month=10, day=1, hour=14, minute=0),
                end=create_dt(year=2010, month=10, day=1, hour=15, minute=0),
            )
            act03 = create_activity(
                title='meet02', busy=True,
                start=create_dt(year=2010, month=10, day=1, hour=18, minute=0),
                end=create_dt(year=2010, month=10, day=1, hour=19, minute=0),
            )

            create_contact = partial(Contact.objects.create, user=user)
            c1 = create_contact(first_name='first_name1', last_name='last_name1')
            c2 = create_contact(first_name='first_name2', last_name='last_name2')

            create_rel = partial(
                Relation.objects.create,
                subject_entity=c1, type_id=constants.REL_SUB_PART_2_ACTIVITY, user=user,
            )
            create_rel(object_entity=act01)
            create_rel(object_entity=act02)
            create_rel(object_entity=act03)

        check_coll = partial(self._check_activity_collisions, participants=[c1, c2])

        try:
            # No collision
            # Next day
            check_coll(
                activity_start=create_dt(year=2010, month=10, day=2, hour=12, minute=0),
                activity_end=create_dt(year=2010,   month=10, day=2, hour=13, minute=0),
            )

            # One minute before
            check_coll(
                activity_start=create_dt(year=2010, month=10, day=1, hour=11, minute=0),
                activity_end=create_dt(year=2010,   month=10, day=1, hour=11, minute=59),
            )

            # One minute after
            check_coll(
                activity_start=create_dt(year=2010, month=10, day=1, hour=13, minute=1),
                activity_end=create_dt(year=2010,   month=10, day=1, hour=13, minute=10),
            )
            # Not busy
            check_coll(
                activity_start=create_dt(year=2010, month=10, day=1, hour=14, minute=0),
                activity_end=create_dt(year=2010,   month=10, day=1, hour=15, minute=0),
                busy=False,
            )
        except ValidationError as e:
            self.fail(str(e))

        # Collision with act01
        # Before
        self.assertRaises(
            ValidationError, self._check_activity_collisions,
            activity_start=create_dt(year=2010, month=10, day=1, hour=11, minute=30),
            activity_end=create_dt(year=2010, month=10, day=1, hour=12, minute=30),
            participants=[c1, c2],
        )

        # After
        self.assertRaises(
            ValidationError, self._check_activity_collisions,
            activity_start=create_dt(year=2010, month=10, day=1, hour=12, minute=30),
            activity_end=create_dt(year=2010, month=10, day=1, hour=13, minute=30),
            participants=[c1, c2],
        )

        # Shorter
        self.assertRaises(
            ValidationError, self._check_activity_collisions,
            activity_start=create_dt(year=2010, month=10, day=1, hour=12, minute=10),
            activity_end=create_dt(year=2010, month=10, day=1, hour=12, minute=30),
            participants=[c1, c2],
        )

        # Longer
        self.assertRaises(
            ValidationError, self._check_activity_collisions,
            activity_start=create_dt(year=2010, month=10, day=1, hour=11, minute=0),
            activity_end=create_dt(year=2010, month=10, day=1, hour=13, minute=30),
            participants=[c1, c2],
        )

        # Busy1
        self.assertRaises(
            ValidationError, self._check_activity_collisions,
            activity_start=create_dt(year=2010, month=10, day=1, hour=17, minute=30),
            activity_end=create_dt(year=2010, month=10, day=1, hour=18, minute=30),
            participants=[c1, c2],
        )

        # Busy2
        self.assertRaises(
            ValidationError, self._check_activity_collisions,
            activity_start=create_dt(year=2010, month=10, day=1, hour=18, minute=0),
            activity_end=create_dt(year=2010, month=10, day=1, hour=18, minute=30),
            busy=False, participants=[c1, c2],
        )


@skipIfCustomActivity
class ICalEncoderTestCase(_ActivitiesTestCase):
    @override_tz('Europe/Paris')
    def test_encode_activity01(self):
        user = self.get_root_user()
        create_dt = self.create_datetime

        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_MEETING)
        activity = Activity.objects.create(
            user=user,
            title='Act#1',
            # busy=True,  # TODO ?
            type_id=sub_type.type_id, sub_type=sub_type,
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
        user = self.get_root_user()
        create_dt = self.create_datetime

        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_PHONECALL_OUTGOING)
        status = self.get_object_or_fail(Status, uuid=constants.UUID_STATUS_PLANNED)
        activity = Activity.objects.create(
            user=user,
            title='My Activity',
            type_id=sub_type.type_id,
            sub_type=sub_type,
            start=create_dt(year=2023, month=3, day=26, hour=14, minute=30),
            end=create_dt(year=2023, month=3, day=26, hour=16),
            place='Tour Eiffel',
            status=status,
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

    def test_ZoneinfoToVtimezone01(self):
        tz = zoneinfo.ZoneInfo('Europe/Paris')
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
            ZoneinfoToVtimezone.generate_vtimezone(
                timezone=tz,
                date_from=datetime(year=2010, month=1, day=1),
                date_to=datetime(year=2010, month=12, day=31),
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
            ZoneinfoToVtimezone.generate_vtimezone(
                timezone=tz,
                date_from=datetime(year=2010, month=1, day=1),
                date_to=datetime(year=2011, month=12, day=31),
            ),
        )

    def test_ZoneinfoToVtimezone02(self):
        tz = zoneinfo.ZoneInfo('Europe/London')
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
            ZoneinfoToVtimezone.generate_vtimezone(
                timezone=tz,
                date_from=datetime(year=2010, month=1, day=1),
                date_to=datetime(year=2010, month=12, day=31),
            ),
        )

    @override_tz('Europe/Paris')
    def test_encode(self):
        user = self.get_root_user()

        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_MEETING)
        create_act = partial(
            Activity.objects.create,
            user=user, busy=True,
            type_id=sub_type.type_id,
            sub_type=sub_type,
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
