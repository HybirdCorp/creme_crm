from datetime import date, time
from functools import partial

from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from parameterized import parameterized

from creme.activities import constants
from creme.activities.forms.fields import ActivitySubTypeField
from creme.activities.models import ActivitySubType, ActivityType
from creme.creme_core.models import Relation

from ..base import Activity, _ActivitiesTestCase, skipIfCustomActivity


@skipIfCustomActivity
class ActivityStartInnerEditionTestCase(_ActivitiesTestCase):
    def test_end(self):
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
    def test_floating(self, field_name):
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

    def test_all_day(self):
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

    def test_busy(self):
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

    def test_floating_time(self):
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

    def test_only_end_time(self):
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

    def test_computed_end(self):
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

    def test_computed_end_all_day(self):
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

    def test_computed_end_all_day__not_round(self):
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

    def test_computed_end_floating_time(self):
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

    def test_collision(self):
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


@skipIfCustomActivity
class ActivitySubTypeInnerEditionTestCase(_ActivitiesTestCase):
    @staticmethod
    def _get_types_uuids_for_field(type_field):
        return {
            str(uid)
            for uid in ActivitySubType.objects.filter(
                pk__in=[c.value for c in type_field.choices if c.value],
            ).values_list('type__uuid', flat=True)
        }

    def _aux_inner_edit_type(self, field_name):
        "Type (& subtype)."
        user = self.login_as_root_and_get()

        create_dt = self.create_datetime
        sub_type1 = self._get_sub_type(constants.UUID_SUBTYPE_PHONECALL_INCOMING)
        activity = Activity.objects.create(
            user=user, title='act01',
            start=create_dt(year=2015, month=1, day=1, hour=14, minute=0),
            end=create_dt(year=2015, month=1, day=1, hour=15, minute=0),
            type_id=sub_type1.type_id, sub_type=sub_type1,
        )

        uri = self.build_inneredit_uri(activity, field_name)

        # GET ---
        response1 = self.assertGET200(uri)

        form_field_name = f'override-{field_name}'

        with self.assertNoException():
            type_f = response1.context['form'].fields[form_field_name]

        self.assertEqual(activity.sub_type_id, type_f.initial)

        # POST ---
        sub_type2 = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_NETWORK)
        self.assertNoFormError(self.client.post(
            uri, data={form_field_name: sub_type2.id},
        ))

        activity = self.refresh(activity)
        self.assertEqual(sub_type2.type_id, activity.type_id)
        self.assertEqual(sub_type2.id,      activity.sub_type_id)

    def test_inner_edit__type(self):
        "Type (& subtype)."
        self._aux_inner_edit_type('type')

    def test_inner_edit__subtype(self):
        "SubType (& type)."
        self._aux_inner_edit_type('sub_type')

    def test_inner_edit__type__exclude_unavailability_choice(self):
        "Exclude <Unavailability> from valid choices."
        user = self.login_as_root_and_get()

        create_dt = self.create_datetime
        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_PHONECALL_INCOMING)
        activity = Activity.objects.create(
            user=user, title='act01',
            start=create_dt(year=2015, month=1, day=1, hour=14, minute=0),
            end=create_dt(year=2015, month=1, day=1, hour=15, minute=0),
            type_id=sub_type.type_id, sub_type=sub_type,
        )

        field_name = 'type'
        form_field_name = f'override-{field_name}'
        excluded_sub_type = ActivitySubType.objects.filter(
            type__uuid=constants.UUID_TYPE_UNAVAILABILITY,
        )[0]
        response = self.assertPOST200(
            self.build_inneredit_uri(activity, field_name),
            data={form_field_name: excluded_sub_type.id},
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field=form_field_name,
            errors=ActivitySubTypeField.default_error_messages['invalid_choice'],
        )

    def test_inner_edit__type__unavailability(self):
        "Unavailability type cannot be changed, the sub_type can."
        user = self.login_as_root_and_get()

        unav_type = self._get_type(constants.UUID_TYPE_UNAVAILABILITY)
        sub_type1 = self._get_sub_type(constants.UUID_SUBTYPE_UNAVAILABILITY)
        sub_type2 = ActivitySubType.objects.create(name='Holidays', type=unav_type)

        create_dt = self.create_datetime
        activity = Activity.objects.create(
            user=user, title='act01',
            start=create_dt(year=2015, month=1, day=1, hour=14, minute=0),
            end=create_dt(year=2015, month=1, day=1, hour=15, minute=0),
            type=unav_type, sub_type=sub_type1,
        )

        field_name = 'type'
        form_field_name = f'override-{field_name}'
        uri = self.build_inneredit_uri(activity, 'type')
        response = self.assertPOST200(
            uri,
            data={
                form_field_name: self._get_sub_type(constants.UUID_SUBTYPE_PHONECALL_INCOMING).id,
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field=form_field_name,
            errors=ActivitySubTypeField.default_error_messages['invalid_choice'],
        )

        self.assertNoFormError(self.client.post(uri, data={form_field_name: sub_type2.id}))

        activity = self.refresh(activity)
        self.assertEqual(unav_type.id, activity.type_id)
        self.assertEqual(sub_type2.id, activity.sub_type_id)

    def test_bulk_edit__type(self):
        "Meeting & Phone-call."
        user = self.login_as_root_and_get()

        create_dt = self.create_datetime
        create_activity = partial(
            Activity.objects.create,
            user=user,
            start=create_dt(year=2015, month=1, day=1, hour=14, minute=0),
            end=create_dt(year=2015, month=1, day=1, hour=15, minute=0),
        )
        sub_type1 = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_OTHER)
        activity1 = create_activity(
            title='act01', type_id=sub_type1.type_id, sub_type=sub_type1,
        )
        sub_type2 = self._get_sub_type(constants.UUID_SUBTYPE_PHONECALL_INCOMING)
        activity2 = create_activity(
            title='act02', type_id=sub_type2.type_id, sub_type=sub_type2,
        )

        field_name = 'type'
        build_uri = partial(self.build_bulkupdate_uri, model=Activity, field=field_name)
        response1 = self.assertGET200(build_uri(entities=[activity1, activity2]))

        formfield_name = f'override-{field_name}'
        with self.assertNoException():
            type_f = response1.context['form'].fields[formfield_name]

        self.assertIsInstance(type_f, ActivitySubTypeField)

        type_uuids = self._get_types_uuids_for_field(type_f)
        self.assertIn(constants.UUID_TYPE_PHONECALL, type_uuids)
        self.assertIn(constants.UUID_TYPE_MEETING,   type_uuids)
        self.assertNotIn(constants.UUID_TYPE_UNAVAILABILITY, type_uuids)

        self.assertFalse(type_f.help_text)

        # ---
        sub_type3 = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_NETWORK)
        self.assertNoFormError(self.client.post(
            build_uri(),
            data={
                'entities': [activity1.pk, activity2.pk],
                formfield_name: sub_type3.id,
            },
        ))

        activity1 = self.refresh(activity1)
        self.assertEqual(sub_type3.type_id, activity1.type_id)
        self.assertEqual(sub_type3.id,      activity1.sub_type_id)

        activity2 = self.refresh(activity2)
        self.assertEqual(sub_type3.type_id, activity2.type_id)
        self.assertEqual(sub_type3.id,      activity2.sub_type_id)

    def test_bulk_edit__type__mixed_unavailability(self):
        "Unavailability cannot be changed when they are mixed with other types."
        user = self.login_as_root_and_get()

        create_dt = self.create_datetime
        create_activity = partial(Activity.objects.create, user=user)
        unav_subtype = self._get_sub_type(constants.UUID_SUBTYPE_UNAVAILABILITY)
        activity1 = create_activity(
            title='act01',
            type=unav_subtype.type,
            sub_type=unav_subtype,
            start=create_dt(year=2024, month=1, day=1, hour=14, minute=0),
            end=create_dt(year=2024, month=1, day=1, hour=15, minute=0),
        )
        phonecall_subtype = self._get_sub_type(constants.UUID_SUBTYPE_PHONECALL_INCOMING)
        activity2 = create_activity(
            title='act02',
            type=phonecall_subtype.type,
            sub_type=phonecall_subtype,
            # More recent, so ordered before activity1, so used as reference
            # instance for global validation
            start=create_dt(year=2024, month=1, day=2, hour=14, minute=0),
            end=create_dt(year=2024, month=1, day=2, hour=15, minute=0),
        )

        field_name = 'type'
        build_uri = partial(self.build_bulkupdate_uri, model=Activity, field=field_name)
        response1 = self.assertGET200(build_uri(entities=[activity1, activity2]))

        formfield_name = f'override-{field_name}'
        with self.assertNoException():
            type_f = response1.context['form'].fields[formfield_name]

        self.assertIsInstance(type_f, ActivitySubTypeField)

        type_uuids = self._get_types_uuids_for_field(type_f)
        self.assertIn(constants.UUID_TYPE_PHONECALL, type_uuids)
        self.assertIn(constants.UUID_TYPE_MEETING,   type_uuids)
        self.assertNotIn(constants.UUID_TYPE_UNAVAILABILITY, type_uuids)

        self.assertEqual(
            ngettext(
                'Beware! The type of {count} activity cannot be changed because'
                ' it is an unavailability.',
                'Beware! The type of {count} activities cannot be changed because'
                ' they are unavailability.',
                1
            ).format(count=1),
            type_f.help_text,
        )

        # ---
        meeting_sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_NETWORK)
        self.assertNoFormError(self.client.post(
            build_uri(),
            data={
                'entities': [activity1.pk, activity2.pk],
                formfield_name: meeting_sub_type.id,
            },
        ))
        activity2 = self.refresh(activity2)
        self.assertEqual(meeting_sub_type.type_id, activity2.type_id)
        self.assertEqual(meeting_sub_type.id,      activity2.sub_type_id)

        # No change
        activity1 = self.refresh(activity1)
        self.assertEqual(unav_subtype.type_id, activity1.type_id)
        self.assertEqual(unav_subtype.id,      activity1.sub_type_id)

    def test_bulk_edit__type__only_unavailability(self):
        "Unavailability type can be changed when they are not mixed with other types."
        user = self.login_as_root_and_get()

        unav_type = self._get_type(constants.UUID_TYPE_UNAVAILABILITY)
        subtype1 = self._get_sub_type(constants.UUID_SUBTYPE_UNAVAILABILITY)
        subtype2 = ActivitySubType.objects.create(name='Holidays', type=unav_type)

        create_dt = self.create_datetime
        create_unav = partial(
            Activity.objects.create, user=user, type=unav_type, sub_type=subtype1,
        )
        activity1 = create_unav(
            title='Unavailability01',
            start=create_dt(year=2015, month=1, day=1, hour=14, minute=0),
            end=create_dt(year=2015, month=1, day=1, hour=15, minute=0),
        )
        activity2 = create_unav(
            title='Unavailability02',
            start=create_dt(year=2015, month=1, day=2, hour=14, minute=0),
            end=create_dt(year=2015, month=1, day=2, hour=15, minute=0),
        )

        field_name = 'type'
        build_uri = partial(self.build_bulkupdate_uri, model=Activity, field='type')
        response1 = self.assertGET200(build_uri(entities=[activity1, activity2]))

        formfield_name = f'override-{field_name}'
        with self.assertNoException():
            type_f = response1.context['form'].fields[formfield_name]

        self.assertSetEqual(
            {constants.UUID_TYPE_UNAVAILABILITY}, self._get_types_uuids_for_field(type_f),
        )
        self.assertFalse(type_f.help_text)

        # ---
        self.assertNoFormError(self.client.post(
            build_uri(),
            data={
                'entities': [activity1.pk, activity2.pk],
                formfield_name: subtype2.id,
            },
        ))
        activity1 = self.refresh(activity1)
        self.assertEqual(unav_type.id, activity1.type_id)
        self.assertEqual(subtype2.id,  activity1.sub_type_id)

        activity2 = self.refresh(activity2)
        self.assertEqual(unav_type.id, activity2.type_id)
        self.assertEqual(subtype2.id, activity2.sub_type_id)
