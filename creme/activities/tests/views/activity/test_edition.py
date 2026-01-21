from functools import partial

from django.utils.translation import gettext as _

from creme.activities import constants
from creme.activities.forms.fields import ActivitySubTypeField
from creme.activities.models import ActivitySubType
from creme.activities.tests.base import (
    Activity,
    _ActivitiesTestCase,
    skipIfCustomActivity,
)
from creme.creme_core.models import Relation


@skipIfCustomActivity
class ActivityEditionTestCase(_ActivitiesTestCase):
    def test_basic(self):
        "Edit title & start."
        user = self.login_as_root_and_get()

        title = 'meet01'
        create_dt = partial(self.create_datetime, year=2013, month=10, day=1)
        start = create_dt(hour=22, minute=0)
        end = create_dt(hour=23, minute=0)
        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_MEETING)
        activity = Activity.objects.create(
            user=user, title=title,
            type_id=sub_type.type_id, sub_type=sub_type,
            start=start, end=end,
        )
        rel = Relation.objects.create(
            subject_entity=user.linked_contact, user=user,
            type_id=constants.REL_SUB_PART_2_ACTIVITY,
            object_entity=activity,
        )

        url = activity.get_edit_absolute_url()

        # GET ---
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            start_f = fields[self.EXTRA_START_KEY]
            end_f = fields[self.EXTRA_END_KEY]
            subtype_f = fields[self.EXTRA_SUBTYPE_KEY]

        self.assertEqual(1,  start_f.initial[0].day)
        self.assertEqual(22, start_f.initial[1].hour)
        self.assertEqual(1,  end_f.initial[0].day)
        self.assertEqual(23, end_f.initial[1].hour)

        self.assertEqual(sub_type.id, subtype_f.initial)

        # POST ---
        title += '_edited'
        self.assertNoFormError(self.client.post(
            url,
            follow=True,
            data={
                'user': user.pk,
                'title': title,
                f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(2011, 2, 22),
                self.EXTRA_SUBTYPE_KEY: sub_type.id,
            },
        ))

        activity = self.refresh(activity)
        self.assertEqual(title, activity.title)
        self.assertEqual(create_dt(year=2011, month=2, day=22), activity.start)
        self.assertEqual(sub_type.type_id, activity.type.id)
        self.assertEqual(sub_type.id,      activity.sub_type_id)

        part_rel = self.get_alone_element(
            Relation.objects.filter(type=constants.REL_SUB_PART_2_ACTIVITY)
        )
        self.assertEqual(rel, part_rel)

    def test_change_time(self):
        user = self.login_as_root_and_get()

        title = 'act01'
        sub_type1 = self._get_sub_type(constants.UUID_SUBTYPE_PHONECALL_INCOMING)
        create_dt = self.create_datetime
        activity = Activity.objects.create(
            user=user, title=title,
            start=create_dt(year=2010, month=10, day=1, hour=14, minute=0),
            end=create_dt(year=2010, month=10, day=1, hour=15, minute=0),
            type_id=sub_type1.type_id, sub_type=sub_type1,
        )

        title += '_edited'
        sub_type2 = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_NETWORK)
        self.assertNoFormError(self.client.post(
            activity.get_edit_absolute_url(),
            follow=True,
            data={
                'user':  user.pk,
                'title': title,
                f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(2011, 2, 22),
                self.EXTRA_SUBTYPE_KEY: sub_type2.id,
            },
        ))

        activity = self.refresh(activity)
        self.assertEqual(title, activity.title)
        self.assertEqual(create_dt(year=2011, month=2, day=22), activity.start)
        self.assertEqual(sub_type2.type_id, activity.type_id)
        self.assertEqual(sub_type2.id,      activity.sub_type_id)

    def test_collision(self):
        user = self.login_as_root_and_get()
        contact = user.linked_contact
        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_OTHER)

        def create_meeting(**kwargs):
            task = Activity.objects.create(
                user=user, type_id=sub_type.type_id, sub_type=sub_type, **kwargs
            )
            Relation.objects.create(
                subject_entity=contact, user=user,
                type_id=constants.REL_SUB_PART_2_ACTIVITY,
                object_entity=task,
            )

            return task

        create_dt = self.create_datetime
        meeting01 = create_meeting(
            title='Meeting#1',
            start=create_dt(year=2013, month=4, day=17, hour=11, minute=0),
            end=create_dt(year=2013,   month=4, day=17, hour=12, minute=0),
        )
        meeting02 = create_meeting(
            title='Meeting#2', busy=True,
            start=create_dt(year=2013, month=4, day=17, hour=14, minute=0),
            end=create_dt(year=2013,   month=4, day=17, hour=15, minute=0),
        )

        response = self.assertPOST200(
            meeting01.get_edit_absolute_url(),
            follow=True,
            data={
                'user':  user.pk,
                'title': meeting01.title,
                'busy':  True,

                f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(2013, 4, 17),
                f'{self.EXTRA_START_KEY}_1': '14:30:00',

                f'{self.EXTRA_END_KEY}_0': self.formfield_value_date(2013, 4, 17),
                f'{self.EXTRA_END_KEY}_1': '16:00:00',

                self.EXTRA_SUBTYPE_KEY: meeting01.sub_type_id,
            }
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field=None,
            errors=_(
                '{participant} already participates in the activity '
                '«{activity}» between {start} and {end}.'
            ).format(
                participant=contact,
                activity=meeting02,
                start='14:30:00',
                end='15:00:00',
            ),
        )

    def test_floating_time(self):
        "Edit FLOATING_TIME activity."
        user = self.login_as_root_and_get()
        task = self._create_activity_by_view(
            user=user,
            **{f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(2013, 7, 25)}
        )
        self.assertEqual(Activity.FloatingType.FLOATING_TIME, task.floating_type)

        response = self.assertGET200(task.get_edit_absolute_url())

        with self.assertNoException():
            fields = response.context['form'].fields
            start_f = fields[self.EXTRA_START_KEY]
            end_f = fields[self.EXTRA_END_KEY]

        self.assertEqual(25, start_f.initial[0].day)
        self.assertIsNone(start_f.initial[1])
        self.assertEqual(25, end_f.initial[0].day)
        self.assertIsNone(end_f.initial[1])

    def test_unavailability(self):
        "Edit an Unavailability: type cannot be changed, sub_type can."
        user = self.login_as_root_and_get()

        sub_type1 = self._get_sub_type(constants.UUID_SUBTYPE_UNAVAILABILITY)
        create_dt = self.create_datetime
        activity = Activity.objects.create(
            user=user, title='act01',
            start=create_dt(year=2015, month=1, day=1, hour=14, minute=0),
            end=create_dt(year=2015, month=1, day=1, hour=15, minute=0),
            type_id=sub_type1.type_id, sub_type=sub_type1,
        )

        url = activity.get_edit_absolute_url()
        data = {
            'user':  user.pk,
            'title': activity.title,

            f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(2015, 1, 1),
            f'{self.EXTRA_START_KEY}_1': '14:30:00',

            f'{self.EXTRA_END_KEY}_0': self.formfield_value_date(2015, 1, 1),
            f'{self.EXTRA_END_KEY}_1': '16:00:00',
        }

        response1 = self.assertPOST200(
            url,
            follow=True,
            data={
                **data,
                self.EXTRA_SUBTYPE_KEY: self._get_sub_type(
                    constants.UUID_SUBTYPE_PHONECALL_INCOMING
                ).id,
            },
        )
        self.assertFormError(
            response1.context['form'],
            field=self.EXTRA_SUBTYPE_KEY,
            errors=ActivitySubTypeField.default_error_messages['invalid_choice'],
        )

        # ---
        sub_type2 = ActivitySubType.objects.create(
            name='Holidays', type_id=sub_type1.type_id,
        )
        response2 = self.client.post(
            url,
            follow=True,
            data={**data, self.EXTRA_SUBTYPE_KEY: sub_type2.id},
        )
        self.assertNoFormError(response2)

        activity = self.refresh(activity)
        self.assertEqual(
            create_dt(year=2015, month=1, day=1, hour=14, minute=30),
            activity.start,
        )
        self.assertEqual(sub_type2.type_id, activity.type_id)
        self.assertEqual(sub_type2.id,      activity.sub_type_id)
