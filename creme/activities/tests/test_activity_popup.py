# -*- coding: utf-8 -*-

from datetime import date, time
from functools import partial

from django.urls import reverse
from django.utils.formats import date_format
from django.utils.translation import gettext as _
from parameterized import parameterized

# from creme.creme_core.models.setting_value import SettingValue
from creme.creme_core.tests.base import CremeTestCase  # skipIfNotInstalled

from .. import constants
from ..models import ActivityType, Calendar
from .base import Activity, _ActivitiesTestCase, skipIfCustomActivity


@skipIfCustomActivity
class ActivityCreatePopupTestCase(_ActivitiesTestCase):
    ACTIVITY_POPUP_CREATION_URL = reverse('activities__create_activity_popup')
    TITLE = 'Meeting activity'

    def build_submit_data(self, user, **kwargs):
        return {
            'user': user.pk,
            'title': self.TITLE,
            self.EXTRA_SUBTYPE_KEY: self._acttype_field_value(
                constants.ACTIVITYTYPE_MEETING,
                constants.ACTIVITYSUBTYPE_MEETING_NETWORK,
            ),
            **kwargs
        }

    @parameterized.expand([
        ({}, 404),
        ({'start': 'invalid'}, 404),
        ({'end': 'invalid'}, 404),
        ({'start': 'invalid', 'end': 'invalid'}, 404),
        ({'start': '2010-01-01T16:35:00', 'end': 'invalid'}, 404),
    ])
    def test_render_invalid_param(self, data, status_code):
        self.login()

        response = self.client.get(self.ACTIVITY_POPUP_CREATION_URL, data=data)
        self.assertEqual(response.status_code, status_code)

    def test_render_not_superuser(self):
        "Not super-user."
        self.login(is_superuser=False, creatable_models=[Activity])
        self.assertGET200(
            self.ACTIVITY_POPUP_CREATION_URL,
            data={'start': '2010-01-01T16:35:00'},
        )

    def test_render_not_allowed(self):
        "Creation perm is needed."
        self.login(is_superuser=False)
        self.assertGET403(
            self.ACTIVITY_POPUP_CREATION_URL,
            data={'start': '2010-01-01T16:35:00'},
        )

    def test_render(self):
        self.login()

        response = self.assertGET200(
            self.ACTIVITY_POPUP_CREATION_URL,
            data={'start': '2010-01-01T16:35:00'},
        )

        context = response.context
        self.assertEqual(Activity.creation_label, context.get('title'))
        self.assertEqual(Activity.save_label,     context.get('submit_label'))

        # It seems TemplateDoesNotExists is not raised in unit tests
        self.assertContains(response, 'name="title"')

        get_initial = context['form'].initial.get
        self.assertTupleEqual(
            (date(2010, 1, 1), time(16, 35)),
            get_initial(self.EXTRA_START_KEY),
        )
        self.assertIsNone(get_initial(self.EXTRA_END_KEY))
        self.assertFalse(get_initial('is_all_day'))

    @parameterized.expand([
        ('2010-01-01T16:35:12', date(2010, 1, 1), time(16, 35)),
        # Beware when it's 23 o clock (bugfix)
        ('2010-01-01T23:16:00', date(2010, 1, 1), time(23, 16)),
        ('2010-01-01T00:00:00', date(2010, 1, 1), None),
    ])
    def test_render_start_only(self, start_iso, start_date, start_time):
        self.login()

        response = self.assertGET200(
            self.ACTIVITY_POPUP_CREATION_URL,
            data={'start': start_iso},
        )

        get_initial = response.context['form'].initial.get
        self.assertTupleEqual(
            (start_date, start_time),
            get_initial(self.EXTRA_START_KEY),
        )
        self.assertIsNone(get_initial(self.EXTRA_END_KEY))
        self.assertFalse(get_initial('is_all_day'))

    def test_render_start_n_end(self):
        self.login()

        response = self.assertGET200(
            self.ACTIVITY_POPUP_CREATION_URL,
            data={
                'start': '2010-01-01T16:35:00',
                'end': '2010-01-01T18:35:00',
            },
        )

        get_initial = response.context['form'].initial.get
        self.assertTupleEqual(
            (date(2010, 1, 1), time(16, 35)),
            get_initial(self.EXTRA_START_KEY),
        )
        self.assertEqual(
            (date(2010, 1, 1), time(18, 35)),
            get_initial(self.EXTRA_END_KEY)
        )
        self.assertFalse(get_initial('is_all_day'))

    def test_render_start_all_day(self):
        self.login()

        response = self.assertGET200(
            self.ACTIVITY_POPUP_CREATION_URL,
            data={
                'start': '2010-01-01T16:35:00',
                'allDay': 'true',
            },
        )

        get_initial = response.context['form'].initial.get
        self.assertEqual(
            (date(2010, 1, 1), time(16, 35)),
            get_initial(self.EXTRA_START_KEY),
        )
        self.assertIsNone(get_initial(self.EXTRA_END_KEY))
        self.assertTrue(get_initial('is_all_day'))

    def test_error_no_participant(self):
        "No participant given."
        user = self.login()

        response = self.assertPOST200(
            self.ACTIVITY_POPUP_CREATION_URL,
            data=self.build_submit_data(
                user,
                **{
                    f'{self.EXTRA_START_KEY}_0': '2010-1-10',
                    f'{self.EXTRA_START_KEY}_1': '09:30:00',

                    f'{self.EXTRA_END_KEY}_0': '2010-1-10',
                    f'{self.EXTRA_END_KEY}_1': '15:00:00',
                }
            ),
        )
        self.assertFormError(response, 'form', None, _('No participant'))

    def test_error_my_participation_no_calendar(self):
        "Selected myself as participant without calendar."
        user = self.login()
        response = self.assertPOST200(
            self.ACTIVITY_POPUP_CREATION_URL,
            data=self.build_submit_data(
                user,
                **{
                    f'{self.EXTRA_START_KEY}_0': '2010-1-10',
                    f'{self.EXTRA_START_KEY}_1': '09:30:00',

                    f'{self.EXTRA_END_KEY}_0': '2010-1-10',
                    f'{self.EXTRA_END_KEY}_1': '15:00:00',

                    f'{self.EXTRA_MYPART_KEY}_0': True,
                }
            ),
        )
        self.assertFormError(
            response, 'form', self.EXTRA_MYPART_KEY,
            _('Enter a value if you check the box.'),
        )

    def test_my_participation(self):
        user = self.login()
        response = self.assertPOST200(
            self.ACTIVITY_POPUP_CREATION_URL,
            data=self.build_submit_data(
                user,
                **{
                    f'{self.EXTRA_START_KEY}_0': '2010-1-10',
                    f'{self.EXTRA_START_KEY}_1': '09:30:00',

                    f'{self.EXTRA_END_KEY}_0': '2010-1-10',
                    f'{self.EXTRA_END_KEY}_1': '15:00:00',

                    f'{self.EXTRA_MYPART_KEY}_0': True,
                    f'{self.EXTRA_MYPART_KEY}_1': Calendar.objects.get_default_calendar(user).pk
                }
            ),
        )

        self.assertNoFormError(response)

        self.assertEqual(1, Activity.objects.count())
        activity = self.get_object_or_fail(Activity, title=self.TITLE)

        create_dt = partial(self.create_datetime, year=2010, month=1, day=10)
        self.assertEqual(create_dt(hour=9, minute=30), activity.start)
        self.assertEqual(create_dt(hour=15), activity.end)
        self.assertEqual(constants.ACTIVITYTYPE_MEETING, activity.type_id)
        self.assertEqual(constants.ACTIVITYSUBTYPE_MEETING_NETWORK, activity.sub_type_id)

    def test_custom_activity_type(self):
        user = self.login()
        custom_type = ActivityType.objects.create(
            id='activities-test_createview_popup3',
            name='Karate session',
            default_day_duration=0,
            default_hour_duration='00:15:00',
            is_custom=True,
        )

        response = self.assertPOST200(
            self.ACTIVITY_POPUP_CREATION_URL,
            data=self.build_submit_data(
                user,
                **{
                    f'{self.EXTRA_START_KEY}_0': '2010-1-10',
                    f'{self.EXTRA_START_KEY}_1': '09:30:00',

                    self.EXTRA_SUBTYPE_KEY: self._acttype_field_value(custom_type.id),

                    f'{self.EXTRA_MYPART_KEY}_0': True,
                    f'{self.EXTRA_MYPART_KEY}_1': Calendar.objects.get_default_calendar(user).pk,
                }
            ),
        )
        self.assertNoFormError(response)

        self.assertEqual(1, Activity.objects.count())
        activity = self.get_object_or_fail(Activity, title=self.TITLE)

        create_dt = partial(self.create_datetime, year=2010, month=1, day=10)
        self.assertEqual(create_dt(hour=9, minute=30), activity.start)
        self.assertEqual(create_dt(hour=9, minute=45), activity.end)
        self.assertEqual(custom_type.id, activity.type_id)
        self.assertIsNone(activity.sub_type_id)

    @parameterized.expand([
        (CremeTestCase.create_datetime(2013, 10, 27),),  # Timezone DST change for Europe/Paris
        (CremeTestCase.create_datetime(2013, 10, 28),),  # No DST change for Europe/Paris
    ])
    def test_DST_transition_allday(self, today):
        "Check that the DST transition works for all-day meetings."
        user = self.login()

        response = self.assertPOST200(
            self.ACTIVITY_POPUP_CREATION_URL,
            data=self.build_submit_data(
                user,
                **{
                    f'{self.EXTRA_START_KEY}_0': date_format(today),

                    f'{self.EXTRA_MYPART_KEY}_0': True,
                    f'{self.EXTRA_MYPART_KEY}_1': Calendar.objects.get_default_calendar(user).pk,
                }
            ),
        )
        self.assertNoFormError(response)

        activity = self.get_object_or_fail(Activity, title=self.TITLE)
        create_today_dt = partial(
            self.create_datetime,
            year=today.year, month=today.month, day=today.day,
        )
        self.assertEqual(create_today_dt(hour=0,  minute=0), activity.start)
        self.assertEqual(create_today_dt(hour=23, minute=59), activity.end)

    # @skipIfNotInstalled('creme.assistants')
    # def test_disabled_informed_users_field(self):
    #     "Setting: no 'informed_users' field."
    #     self.login()
    #
    #     sv = self.get_object_or_fail(SettingValue, key_id=constants.SETTING_FORM_USERS_MSG)
    #     sv.value = False
    #     sv.save()
    #
    #     response = self.assertGET200(
    #         self.ACTIVITY_POPUP_CREATION_URL,
    #         data={'start': '2010-01-01T16:30:00'},
    #     )
    #
    #     self.assertNotIn('informed_users', response.context['form'].fields)
