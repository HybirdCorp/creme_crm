from datetime import date, time
from functools import partial

from django.utils.translation import gettext as _
from parameterized import parameterized

from creme.creme_core.models import Relation
from creme.creme_core.tests.base import CremeTestCase

from .. import constants
from ..forms.bulk_update import ActivityRangeField
from ..forms.fields import DateWithOptionalTimeField
from ..models import ActivitySubType, ActivityType
from .base import Activity, _ActivitiesTestCase, skipIfCustomActivity


class ActivityRangeFieldTestCase(CremeTestCase):
    def test_range(self):
        DWOT = DateWithOptionalTimeField.DateWithOptionalTime

        def build_range(**kwargs):
            return ActivityRangeField.Range(**{
                'start': DWOT(date=date(year=2023, month=6, day=22), time=time(hour=14, minute=0)),
                'end': DWOT(date=date(year=2023, month=6, day=22), time=time(hour=16, minute=30)),
                'all_day': False,
                'busy': True,
                **kwargs
            })

        act_range = build_range()
        self.assertEqual(
            DWOT(date=date(year=2023, month=6, day=22), time=time(hour=14, minute=0)),
            act_range.start,
        )
        self.assertEqual(
            DWOT(date=date(year=2023, month=6, day=22), time=time(hour=16, minute=30)),
            act_range.end,
        )
        self.assertIs(act_range.all_day, False)
        self.assertIs(act_range.busy, True)

        self.assertEqual(build_range(), act_range)
        self.assertNotEqual(None, act_range)
        self.assertNotEqual(build_range(all_day=True), act_range)
        self.assertNotEqual(build_range(busy=False),   act_range)
        self.assertNotEqual(build_range(start=None),   act_range)

    def test_clean_empty_required(self):
        field = ActivityRangeField(required=True)
        msg = _('This field is required.')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=None)
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=[])

    def test_clean_empty_not_required(self):
        field = ActivityRangeField(required=False)
        self.assertIsNone(field.clean([]))
        self.assertIsNone(field.clean(['']))
        self.assertIsNone(field.clean(['', '']))

    def test_clean_complete(self):
        field = ActivityRangeField()

        DWOT = DateWithOptionalTimeField.DateWithOptionalTime
        self.assertEqual(
            field.Range(
                start=DWOT(date=date(year=2022, month=10, day=20), time=time(hour=18, minute=30)),
                end=DWOT(date=date(year=2022, month=10, day=21), time=time(hour=12, minute=00)),
                all_day=False,
                busy=True,
            ),
            field.clean([
                [self.formfield_value_date(2022, 10, 20), '18:30:00'],
                [self.formfield_value_date(2022, 10, 21), '12:00:00'],
                '',
                'on',
            ]),
        )

    def test_clean_partial_datetime(self):
        field = ActivityRangeField()

        DWOT = DateWithOptionalTimeField.DateWithOptionalTime
        self.assertEqual(
            field.Range(
                start=DWOT(date=date(year=2023, month=3, day=15), time=time(hour=14, minute=45)),
                end=DWOT(date=date(year=2023, month=3, day=16)),
                all_day=True,
                busy=False,
            ),
            field.clean([
                [self.formfield_value_date(2023, 3, 15), '14:45:00'],
                [self.formfield_value_date(2023, 3, 16)],
                'on',
                '',
            ]),
        )

    def test_clean_partial_not_required(self):
        field = ActivityRangeField(required=False)
        DWOT = DateWithOptionalTimeField.DateWithOptionalTime
        self.assertEqual(
            field.Range(
                start=DWOT(date=date(year=2023, month=3, day=15), time=time(hour=14, minute=45)),
                end=None,
                all_day=False,
                busy=False,
            ),
            field.clean([
                [self.formfield_value_date(2023, 3, 15), '14:45:00'],
                ['', ''],
                '',
                '',
            ]),
        )
        self.assertEqual(
            field.Range(
                start=None,
                end=DWOT(date=date(year=2023, month=3, day=16)),
                all_day=False,
                busy=False,
            ),
            field.clean([
                ['', ''],
                [self.formfield_value_date(2023, 3, 16), ''],
                '',
                '',
            ]),
        )


@skipIfCustomActivity
class ActivityInnerEditionTestCase(_ActivitiesTestCase):
    def test_start_n_end(self):
        user = self.login_as_root_and_get()
        activity = self._create_meeting(user=user, busy=True)

        Relation.objects.create(
            user=user,
            subject_entity=user.linked_contact,
            type_id=constants.REL_SUB_PART_2_ACTIVITY,
            object_entity=activity,
        )

        field_name = 'start'
        url = self.build_inneredit_uri(activity, field_name)
        response1 = self.assertGET200(url)

        with self.assertNoException():
            value_f = response1.context['form'].fields[f'override-{field_name}']

        self.assertTupleEqual(
            (
                (date(year=2013, month=4, day=1), time(hour=14)),
                (date(year=2013, month=4, day=1), time(hour=15)),
                False,
                True,
            ),
            value_f.initial,
        )

        # ---
        data = {
            # START
            f'override-{field_name}_0_0': self.formfield_value_date(2022, 10, 14),
            f'override-{field_name}_0_1': '14:30:00',

            # END
            f'override-{field_name}_1_0': self.formfield_value_date(2022, 10, 14),
            f'override-{field_name}_1_1': '08:15:00',
        }
        response2 = self.assertPOST200(url, data=data)
        self.assertFormError(
            response2.context['form'],
            field=f'override-{field_name}', errors=_('End is before start'),
        )

        # ---
        self.assertNoFormError(self.client.post(
            url,
            data={
                **data,

                # End date
                f'override-{field_name}_1_0': self.formfield_value_date(2022, 10, 15),
            },
        ))

        activity = self.refresh(activity)
        self.assertEqual(
            self.create_datetime(year=2022, month=10, day=14, hour=14, minute=30),
            activity.start,
        )
        self.assertEqual(
            self.create_datetime(year=2022, month=10, day=15, hour=8, minute=15),
            activity.end,
        )
        self.assertEqual(Activity.FloatingType.NARROW, activity.floating_type)
        self.assertFalse(activity.is_all_day)
        self.assertFalse(activity.busy)

    @parameterized.expand([
        'start',
        'end',
        'is_all_day',
        'busy',
    ])
    def test_start_floating(self, field_name):
        user = self.login_as_root_and_get()
        activity = self._create_meeting(user=user)

        url = self.build_inneredit_uri(activity, field_name)

        # ---
        response1 = self.assertPOST200(
            url,
            data={
                # END
                f'override-{field_name}_1_0': self.formfield_value_date(2022, 10, 15),
                f'override-{field_name}_1_1': '08:15:00',
            },
        )
        self.assertFormError(
            response1.context['form'],
            field=f'override-{field_name}',
            errors=_("You can't set the end of your activity without setting its start"),
        )

        # ---
        self.assertNoFormError(self.client.post(url, data={}))
        activity = self.refresh(activity)

        self.assertIsNone(activity.start)
        self.assertIsNone(activity.end)
        self.assertEqual(Activity.FloatingType.FLOATING, activity.floating_type)
        self.assertFalse(activity.is_all_day)
        self.assertFalse(activity.busy)

    def test_start_all_day(self):
        user = self.login_as_root_and_get()
        activity = self._create_meeting(user=user)

        field_name = 'start'
        self.assertNoFormError(self.client.post(
            self.build_inneredit_uri(activity, field_name),
            data={
                # START
                f'override-{field_name}_0_0': self.formfield_value_date(2022, 10, 14),

                # END
                # f'override-{field_name}_1_0': ...,

                # ALL DAY
                f'override-{field_name}_2': 'on',
            },
        ))
        activity = self.refresh(activity)
        self.assertTrue(activity.is_all_day)
        self.assertEqual(Activity.FloatingType.NARROW, activity.floating_type)
        self.assertFalse(activity.busy)

        create_dt = partial(self.create_datetime, year=2022, month=10, day=14)
        self.assertEqual(create_dt(hour=0,  minute=0),  activity.start)
        self.assertEqual(create_dt(hour=23, minute=59), activity.end)

    def test_start_busy(self):
        user = self.login_as_root_and_get()
        activity = self._create_meeting(user=user)

        field_name = 'start'
        self.assertNoFormError(self.client.post(
            self.build_inneredit_uri(activity, field_name),
            data={
                # START
                f'override-{field_name}_0_0': self.formfield_value_date(2022, 10, 19),
                f'override-{field_name}_0_1': '08:00:00',

                # END
                f'override-{field_name}_1_0': self.formfield_value_date(2022, 10, 19),
                f'override-{field_name}_1_1': '12:00:00',

                # BUSY
                f'override-{field_name}_3': 'on',
            },
        ))
        activity = self.refresh(activity)
        self.assertTrue(activity.busy)
        self.assertFalse(activity.is_all_day)
        self.assertEqual(Activity.FloatingType.NARROW, activity.floating_type)

        create_dt = partial(self.create_datetime, year=2022, month=10, day=19)
        self.assertEqual(create_dt(hour=8),  activity.start)
        self.assertEqual(create_dt(hour=12), activity.end)

    def test_start_floating_time(self):
        user = self.login_as_root_and_get()
        activity = self._create_meeting(user=user)

        field_name = 'start'
        url = self.build_inneredit_uri(activity, field_name)
        data = {
            # START
            f'override-{field_name}_0_0': self.formfield_value_date(2022, 10, 14),

            # END
            f'override-{field_name}_1_0': self.formfield_value_date(2022, 10, 15),
        }

        # ---
        response1 = self.assertPOST200(
            url,
            data={**data, f'override-{field_name}_3': 'on'},
        )
        self.assertFormError(
            response1.context['form'],
            field=f'override-{field_name}',
            errors=_("A floating on the day activity can't busy its participants"),
        )

        # ---
        self.assertNoFormError(self.client.post(url, data=data))

        activity = self.refresh(activity)
        self.assertEqual(Activity.FloatingType.FLOATING_TIME, activity.floating_type)
        self.assertFalse(activity.is_all_day)
        self.assertFalse(activity.busy)

        create_dt = partial(self.create_datetime, year=2022, month=10)
        self.assertEqual(create_dt(day=14, hour=0,  minute=0),  activity.start)
        self.assertEqual(create_dt(day=15, hour=23, minute=59), activity.end)

    def test_start_only_end_time(self):
        user = self.login_as_root_and_get()
        activity = self._create_meeting(user=user)

        field_name = 'start'
        self.assertNoFormError(self.client.post(
            self.build_inneredit_uri(activity, field_name),
            data={
                # START
                f'override-{field_name}_0_0': self.formfield_value_date(2022, 9, 17),
                f'override-{field_name}_0_1': '8:30:00',

                # END
                # f'override-{field_name}_1_0': ...,
                f'override-{field_name}_1_1': '12:15:00',
            },
        ))

        activity = self.refresh(activity)
        self.assertEqual(
            self.create_datetime(year=2022, month=9, day=17, hour=8, minute=30),
            activity.start,
        )
        self.assertEqual(
            self.create_datetime(year=2022, month=9, day=17, hour=12, minute=15),
            activity.end,
        )
        self.assertEqual(Activity.FloatingType.NARROW, activity.floating_type)
        self.assertFalse(activity.is_all_day)
        self.assertFalse(activity.busy)

    def test_start_computed_end(self):
        user = self.login_as_root_and_get()
        activity = self._create_meeting(user=user)

        act_type = activity.type
        self.assertEqual(0, act_type.default_day_duration)
        self.assertEqual('00:15:00', act_type.default_hour_duration)

        field_name = 'start'
        self.assertNoFormError(self.client.post(
            self.build_inneredit_uri(activity, field_name),
            data={
                # START
                f'override-{field_name}_0_0': self.formfield_value_date(2023, 1, 20),
                f'override-{field_name}_0_1': '8:30:00',
            },
        ))

        activity = self.refresh(activity)
        self.assertEqual(
            self.create_datetime(year=2023, month=1, day=20, hour=8, minute=30),
            activity.start,
        )
        self.assertEqual(
            self.create_datetime(year=2023, month=1, day=20, hour=8, minute=45),
            activity.end,
        )
        self.assertEqual(Activity.FloatingType.NARROW, activity.floating_type)
        self.assertFalse(activity.is_all_day)
        self.assertFalse(activity.busy)

    def test_start_computed_end_all_day01(self):
        user = self.login_as_root_and_get()

        atype = ActivityType.objects.create(
            name='Martial contest',
            default_day_duration=2,
            default_hour_duration='00:00:00',
        )
        sub_type = ActivitySubType.objects.create(name='Karate contest', type=atype)

        create_dt = self.create_datetime
        activity = Activity.objects.create(
            user=user, title='My Activity',
            type=atype, sub_type=sub_type,
            start=create_dt(year=2022, month=10, day=19, hour=8),
            end=create_dt(year=2022,   month=10, day=20, hour=20),
        )

        field_name = 'start'
        self.assertNoFormError(self.client.post(
            self.build_inneredit_uri(activity, field_name),
            data={
                # START
                f'override-{field_name}_0_0': self.formfield_value_date(2023, 1, 20),
                f'override-{field_name}_0_1': '8:30:00',

                f'override-{field_name}_2': 'on',
            },
        ))

        activity = self.refresh(activity)
        self.assertEqual(
            self.create_datetime(year=2023, month=1, day=20, hour=0, minute=0),
            activity.start,
        )
        self.assertEqual(
            self.create_datetime(year=2023, month=1, day=21, hour=23, minute=59),
            activity.end,
        )
        self.assertTrue(activity.is_all_day)
        self.assertEqual(Activity.FloatingType.NARROW, activity.floating_type)

    def test_start_computed_end_all_day02(self):
        "Duration is not a round number of days."
        user = self.login_as_root_and_get()

        atype = ActivityType.objects.create(
            name='Martial contest',
            default_day_duration=2, default_hour_duration='05:00:00',
        )
        sub_type = ActivitySubType.objects.create(name='Karate contest', type=atype)

        create_dt = self.create_datetime
        activity = Activity.objects.create(
            user=user, title='My Activity',
            type=atype, sub_type=sub_type,
            start=create_dt(year=2022, month=10, day=19, hour=8),
            end=create_dt(year=2022,   month=10, day=20, hour=20),
        )

        field_name = 'start'
        self.assertNoFormError(self.client.post(
            self.build_inneredit_uri(activity, field_name),
            data={
                # START
                f'override-{field_name}_0_0': self.formfield_value_date(2023, 1, 20),
                f'override-{field_name}_0_1': '8:30:00',

                f'override-{field_name}_2': 'on',
            },
        ))

        activity = self.refresh(activity)
        self.assertEqual(
            self.create_datetime(year=2023, month=1, day=20, hour=0, minute=0),
            activity.start,
        )
        self.assertEqual(
            self.create_datetime(year=2023, month=1, day=22, hour=23, minute=59),
            activity.end,
        )
        self.assertTrue(activity.is_all_day)

    def test_start_computed_end_floating_time(self):
        user = self.login_as_root_and_get()

        atype = ActivityType.objects.create(
            name='Martial contest',
            default_day_duration=2,
            default_hour_duration='00:00:00',
        )
        sub_type = ActivitySubType.objects.create(name='Karate contest', type=atype)

        create_dt = self.create_datetime
        activity = Activity.objects.create(
            user=user, title='My Activity',
            type=atype,  sub_type=sub_type,
            start=create_dt(year=2022, month=10, day=19, hour=8),
            end=create_dt(year=2022,   month=10, day=20, hour=20),
        )

        field_name = 'start'
        self.assertNoFormError(self.client.post(
            self.build_inneredit_uri(activity, field_name),
            data={
                # START
                f'override-{field_name}_0_0': self.formfield_value_date(2023, 1, 20),
            },
        ))

        activity = self.refresh(activity)
        self.assertEqual(
            self.create_datetime(year=2023, month=1, day=20, hour=0, minute=0),
            activity.start,
        )
        self.assertEqual(
            self.create_datetime(year=2023, month=1, day=21, hour=23, minute=59),
            activity.end,
        )
        self.assertFalse(activity.is_all_day)
        self.assertEqual(Activity.FloatingType.FLOATING_TIME, activity.floating_type)

    def test_start_collision(self):
        user = self.login_as_root_and_get()

        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_NETWORK)
        create_activity = partial(
            Activity.objects.create,
            user=user, type_id=sub_type.type_id, sub_type=sub_type,
        )
        create_dt = self.create_datetime
        activity1 = create_activity(
            title='Activity #1',
            start=create_dt(year=2022, month=10, day=19, hour=14),
            end=create_dt(year=2022,   month=10, day=19, hour=16),
        )
        activity2 = create_activity(
            title='Activity #2',
            start=create_dt(year=2022, month=10, day=20, hour=15),
            end=create_dt(year=2022,   month=10, day=20, hour=17),
            busy=True,
        )

        contact = user.linked_contact

        create_rel = partial(
            Relation.objects.create,
            user=user, type_id=constants.REL_SUB_PART_2_ACTIVITY
        )
        create_rel(subject_entity=contact, object_entity=activity1)
        create_rel(subject_entity=contact, object_entity=activity2)

        field_name = 'start'
        url = self.build_inneredit_uri(activity1, field_name)

        # ---
        data = {
            # START
            f'override-{field_name}_0_0': self.formfield_value_date(2022, 10, 20),
            f'override-{field_name}_0_1': '14:00:00',

            # END
            f'override-{field_name}_1_0': self.formfield_value_date(2022, 10, 20),
            f'override-{field_name}_1_1': '16:00:00',
        }
        response1 = self.assertPOST200(url, data=data)
        self.assertFormError(
            response1.context['form'],
            field=f'override-{field_name}',
            errors=_(
                '{participant} already participates in the activity '
                '«{activity}» between {start} and {end}.'
            ).format(
                participant=contact,
                activity=activity2,
                start='15:00:00',
                end='16:00:00',
            ),
        )

        # ---
        self.assertNoFormError(self.client.post(
            url,
            data={
                **data,

                # End time
                f'override-{field_name}_1_1': '15:00:00',
            },
        ))
