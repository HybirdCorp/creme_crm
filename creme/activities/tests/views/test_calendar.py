from datetime import timedelta
from functools import partial
from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.models import Session
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.html import escape
from django.utils.timezone import now
from django.utils.timezone import override as override_tz
from django.utils.timezone import zoneinfo
from django.utils.translation import gettext as _
from parameterized import parameterized

from creme.activities import constants
from creme.activities.bricks import CalendarsBrick
from creme.activities.models import Calendar, CalendarConfigItem
from creme.creme_core.creme_jobs import deletor_type
from creme.creme_core.models import DeletionCommand, Job, Relation
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin

from ..base import Activity, _ActivitiesTestCase, skipIfCustomActivity


class CalendarPageViewsTestCase(_ActivitiesTestCase):
    CALENDAR_URL = reverse('activities__calendar')
    UPDATE_URL = reverse('activities__set_activity_dates')

    @staticmethod
    def _build_ts(dt):
        return dt.isoformat()

    def _get_cal_activities(self, calendars, start=None, end=None, status=200):
        data = {'calendar_id': [str(c.id) for c in calendars]}

        if start:
            data['start'] = start

        if end:
            data['end'] = end

        return self.assertGET(
            status,
            reverse('activities__calendars_activities'),
            data=data,
        )

    @staticmethod
    def _get_user_sessions(user):
        user_id = str(user.id)

        return [
            d for d in (s.get_decoded() for s in Session.objects.all())
            if d.get('_auth_user_id') == user_id
        ]

    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=False)
    def test_calendar_view__no_selected_calendar(self):
        "No calendars selected; default calendar exists."
        user = self.login_as_root_and_get()
        other_user = self.create_user()
        def_cal = self.assertUserHasDefaultCalendar(user)

        response = self.assertGET200(self.CALENDAR_URL)
        self.assertTemplateUsed(response, 'activities/calendar.html')

        with self.assertNoException():
            ctxt = response.context
            floating_acts = ctxt['floating_activities']
            my_cals = ctxt['my_calendars']
            my_cal_ids = ctxt['my_selected_calendar_ids']
            others_calendars = ctxt['others_calendars']
            other_cal_ids = ctxt['others_selected_calendar_ids']
            enable_calendars_search = ctxt['enable_calendars_search']
            enable_floating_search = ctxt['enable_floating_activities_search']

        self.assertSetEqual({def_cal.id}, my_cal_ids, Calendar.objects.values('id', 'name'))
        self.assertSetEqual(set(), other_cal_ids)

        self.assertFalse(floating_acts)
        self.assertListEqual([def_cal], [*my_cals])

        self.assertIsList(others_calendars)
        self.assertIsNone(dict(others_calendars).get(other_user))

        self.assertIs(enable_calendars_search, False)
        self.assertIs(enable_floating_search, False)

    @skipIfCustomActivity
    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=None)
    def test_calendar_view__floating(self):
        "Some calendars selected; floating activities."
        user = self.login_as_super(index=0)
        other_user = self.create_user(index=1)
        staff_user = self.create_user(index=2, is_staff=True)
        inactive_user = self.create_user(index=3, is_active=False)

        create_cal = Calendar.objects.create
        cal1 = create_cal(user=user,       is_default=True, name='Cal #1')
        cal2 = create_cal(user=other_user, is_default=True, name='Cal #2', is_public=True)
        cal3 = create_cal(user=other_user, name='Cal #3', is_public=False)
        cal4 = create_cal(user=other_user, name='Cal #4', is_public=True)
        create_cal(user=staff_user,    name='Cal #5', is_public=True)  # Should not be used
        create_cal(user=inactive_user, name='Cal #6', is_public=True)  # Should not be used

        sub_type1 = self._get_sub_type(constants.UUID_SUBTYPE_PHONECALL_OUTGOING)
        sub_type2 = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_QUALIFICATION)
        create_act = partial(
            Activity.objects.create, user=user,
            type_id=sub_type1.type_id, sub_type=sub_type1,
            floating_type=Activity.FloatingType.FLOATING,
        )
        act1 = create_act(title='Act#1')
        act2 = create_act(
            title='Act#2',
            type_id=sub_type2.type_id, sub_type=sub_type2,
        )
        act3 = create_act(title='Act#3', is_deleted=True)
        act4 = create_act(title='Act#4', user=other_user)
        act5 = create_act(title='Act#5', floating_type=Activity.FloatingType.NARROW)

        create_rel = partial(
            Relation.objects.create, user=user,
            subject_entity=user.linked_contact,
            type_id=constants.REL_SUB_PART_2_ACTIVITY,
        )
        create_rel(object_entity=act1)
        act1.calendars.add(cal1)
        create_rel(object_entity=act2)
        act2.calendars.add(cal1)
        create_rel(object_entity=act3)
        act3.calendars.add(cal1)
        create_rel(object_entity=act4)
        act4.calendars.add(cal1)
        create_rel(object_entity=act5)
        act5.calendars.add(cal1)

        response = self.assertGET200(
            self.CALENDAR_URL,
            data={'calendar_id': [cal1.id, cal2.id, cal3.id]},
        )

        with self.assertNoException():
            ctxt = response.context
            floating_acts = ctxt['floating_activities']
            my_cals = ctxt['my_calendars']
            my_cal_ids = ctxt['my_selected_calendar_ids']
            others_calendars = dict(ctxt['others_calendars'])
            other_cal_ids = ctxt['others_selected_calendar_ids']

        self.assertCountEqual([act1, act2, act4], floating_acts)
        self.assertCountEqual([cal1], my_cals)
        self.assertSetEqual({cal1.id}, my_cal_ids)

        self.assertCountEqual([cal2, cal4], others_calendars.get(other_user))
        self.assertNotIn(staff_user,    others_calendars)
        self.assertNotIn(inactive_user, others_calendars)

        self.assertSetEqual({cal2.id}, other_cal_ids)

    @skipIfCustomActivity
    def test_calendar_view__floating_without_calendar(self):
        "Floating activity without calendar (bugfix)."
        user = self.login_as_root_and_get()

        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_OTHER)

        def create_act(i):
            act = Activity.objects.create(
                user=user, title=f'Floating Act#{i}',
                type_id=sub_type.type_id,
                sub_type=sub_type,
                floating_type=Activity.FloatingType.FLOATING,
            )
            Relation.objects.create(
                user=user,
                subject_entity=user.linked_contact,
                type_id=constants.REL_SUB_PART_2_ACTIVITY,
                object_entity=act,
            )
            return act

        create_act(1)
        act2 = create_act(2)
        act2.calendars.add(Calendar.objects.get_default_calendar(user))

        response = self.assertGET200(self.CALENDAR_URL)

        with self.assertNoException():
            floating_acts = response.context['floating_activities']

        self.assertListEqual([act2], [*floating_acts])

    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=None)
    def test_calendar_view__no_default(self):
        "No calendars selected ; no default calendar => a default calendar is created."
        user = self.login_as_super()
        self.assertFalse(Calendar.objects.filter(is_default=True, user=user))

        response = self.assertGET200(self.CALENDAR_URL)
        def_cal = self.assertUserHasDefaultCalendar(user)
        self.assertFalse(def_cal.is_public)
        self.assertSetEqual(
            {def_cal.id},
            response.context.get('my_selected_calendar_ids'),
            Calendar.objects.values('id', 'name'),
        )

    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=None)
    def test_calendar_view__no_calendar(self):
        "No calendar => a default public calendar is created."
        user = self.login_as_super()
        self.assertFalse(Calendar.objects.filter(is_default=True, user=user))

        with override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=True):
            self.assertGET200(self.CALENDAR_URL)

            def_cal = self.assertUserHasDefaultCalendar(user)
            self.assertTrue(def_cal.is_public)

    @parameterized.expand([
        ('Europe/London', 0, 60),  # UTC / UTC+1:00
        ('Europe/Paris', 60, 120),  # UTC+1:00 / UTC+2:00
        ('America/New_York', -5 * 60, -4 * 60),  # UTC-5:00 / UTC-4:00
    ])
    def test_calendar_view__utc_offset(self, timezone_name, without_dst, with_dst):
        user = self.login_as_super()
        config = CalendarConfigItem.objects.for_user(user)

        with override_tz(timezone_name):
            dst_date = self.create_datetime(2023, 8, 1)
            no_dst_date = self.create_datetime(2023, 12, 1)

            self.assertTrue(dst_date.tzinfo.dst(dst_date).total_seconds() != 0)
            self.assertTrue(no_dst_date.tzinfo.dst(no_dst_date).total_seconds() == 0)

            with patch('creme.activities.utils.now', return_value=dst_date):
                response = self.assertGET200(self.CALENDAR_URL)
                settings = response.context['calendar_settings']

                self.assertEqual({
                    **config.as_dict(),
                    "utc_offset": with_dst
                }, settings)

            with patch('creme.activities.utils.now', return_value=no_dst_date):
                response = self.assertGET200(self.CALENDAR_URL)
                settings = response.context['calendar_settings']

                self.assertEqual({
                    **config.as_dict(),
                    "utc_offset": without_dst
                }, settings)

    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=None)
    def test_calendar_view__is_staff(self):
        "No calendars selected ; no default calendar => a default calendar is created."
        user = self.login_as_super(is_staff=True)
        self.assertFalse(Calendar.objects.filter(is_default=True, user=user))

        response = self.assertGET200(self.CALENDAR_URL)
        def_cal = self.assertUserHasDefaultCalendar(user)
        self.assertFalse(def_cal.is_public)
        self.assertSetEqual(
            {def_cal.id},
            response.context.get('my_selected_calendar_ids'),
            Calendar.objects.values('id', 'name'),
        )

    def test_activities_data__one_user__empty(self):
        "One user, no Activity."
        user = self.login_as_root_and_get()

        response = self._get_cal_activities([Calendar.objects.get_default_calendar(user)])
        self.assertEqual('application/json', response['Content-Type'])
        self.assertListEqual([], response.json())

    @skipIfCustomActivity
    @parameterized.expand([
        (
            "Europe/Paris",
            (2013, 3, 1),
            (2013, 3, 1),
            False,
            '2013-03-01T00:00:00',
            '2013-03-01T00:00:00',
        ), (
            "America/New_York",
            (2013, 3, 1),
            (2013, 3, 5, 11),
            False,
            '2013-03-01T00:00:00',
            '2013-03-05T11:00:00',
        ), (
            # All day => ends on 00:00 of the next day
            "Europe/Paris",
            (2013, 3, 1),
            (2013, 3, 1),
            True,
            '2013-03-01T00:00:00',
            '2013-03-02T00:00:00',
        ), (
            # All day => ends on 00:00 of the next day
            "America/New_York",
            (2013, 3, 1),
            (2013, 3, 1),
            True,
            '2013-03-01T00:00:00',
            '2013-03-02T00:00:00',
        ), (
            # All day => ends on 00:00 of the next day
            "Europe/Paris",
            (2013, 3, 1),
            (2013, 3, 5, 11),
            True,
            '2013-03-01T00:00:00',
            '2013-03-06T00:00:00',
        ),
    ])
    def test_activities_data__one_user__one_event(
        self, tzname, start, end, is_all_day, data_start, data_end
    ):
        user = self.login_as_root_and_get()
        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_PHONECALL_OUTGOING)

        with override_tz(zoneinfo.ZoneInfo(tzname)):
            start = CremeTestCase.create_datetime(*start)
            end = CremeTestCase.create_datetime(*end)

            calendar = Calendar.objects.get_default_calendar(user)
            activity = Activity.objects.create(
                title='Act#1',
                user=user,
                type_id=sub_type.type_id,
                sub_type=sub_type,
                start=start,
                end=end,
                is_all_day=is_all_day,
            )
            activity.calendars.set([calendar])
            activity.handle_all_day()
            activity.save()

            response = self.assertGET200(
                reverse('activities__calendars_activities'),
                data={
                    'calendar_id': calendar.pk,
                    'start': start.isoformat(),
                    'end': end.isoformat(),
                },
            )

            self.assertListEqual(
                [{
                    'id':       activity.id,
                    'title':    'Act#1',
                    'start':    data_start,
                    'end':      data_end,
                    'allDay':   is_all_day,
                    'calendar': calendar.pk,
                    'color':    f'#{calendar.color}',
                    'url':      reverse('activities__view_activity_popup', args=(activity.id,)),
                    'editable': True,
                    'busy':     False,
                    'type':     _('Phone call'),
                }],
                response.json()
            )

    @skipIfCustomActivity
    def test_activities_data__one_user__several_activities(self):
        user = self.login_as_root_and_get()
        cal = Calendar.objects.get_default_calendar(user)
        Calendar.objects.create(user=user, name='Other Cal #1', is_custom=True)

        create_dt = self.create_datetime
        start = create_dt(year=2013, month=3, day=1)
        end   = create_dt(year=2013, month=3, day=31, hour=23, minute=59)

        sub_type1 = self._get_sub_type(constants.UUID_SUBTYPE_PHONECALL_INCOMING)
        create = partial(
            Activity.objects.create,
            user=user,
            type_id=sub_type1.type_id,
            sub_type=sub_type1,
        )
        act0 = create(title='Act#0', start=start, end=start)
        act1 = create(
            title='Act#1',
            start=start + timedelta(days=1), end=start + timedelta(days=2),
        )
        # Not in calendar
        create(
            title='Act#2',
            start=start + timedelta(days=1), end=start + timedelta(days=2),
        )
        # Start OK
        sub_type3 = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_QUALIFICATION)
        act3 = create(
            title='Act#3',
            start=start + timedelta(days=2), end=end + timedelta(days=1),
            is_all_day=True,
            type_id=sub_type3.type_id,
            sub_type=sub_type3,
        )
        # End OK
        act4 = create(
            title='Act#4',
            start=start - timedelta(days=1), end=start + timedelta(days=3),
        )
        act5 = create(
            title='Act#5',
            start=start + timedelta(days=5), end=start + timedelta(days=5, hours=3),
            is_deleted=True,
        )

        for act in (act0, act1, act3, act4, act5):
            act.calendars.set([cal])

        create_rel = partial(
            Relation.objects.create,
            user=user, type_id=constants.REL_SUB_PART_2_ACTIVITY,
        )
        create_rel(subject_entity=user.linked_contact,            object_entity=act3)
        create_rel(subject_entity=self.create_user().linked_contact, object_entity=act3)

        response = self._get_cal_activities(
            [cal], start=start.isoformat(), end=end.isoformat(),
        )

        data = response.json()
        self.assertEqual(4, len(data))

        def build_popup_url(act):
            return reverse('activities__view_activity_popup', args=(act.id,))

        self.assertDictEqual(
            {
                'id':         act3.id,
                'title':      'Act#3',
                'start':      '2013-03-03T00:00:00',
                # On fullcalendar side a full day ends on the next day at 00:00:00
                'end':        '2013-04-02T00:00:00',
                'allDay':     True,
                'calendar':   cal.id,
                'color':      f'#{cal.color}',
                'url':        build_popup_url(act3),
                'editable':   True,
                'busy':       False,
                'type':       _('Meeting'),
            },
            data[0],
        )
        self.assertDictEqual(
            {
                'id':         act1.id,
                'title':      'Act#1',
                'start':      '2013-03-02T00:00:00',
                'end':        '2013-03-03T00:00:00',
                'allDay':     False,
                'calendar':   cal.id,
                'color':      f'#{cal.color}',
                'url':        build_popup_url(act1),
                'editable':   True,
                'busy':       False,
                'type':       _('Phone call'),
            },
            data[1],
        )
        self.assertDictEqual(
            {
                'id':         act0.id,
                'title':      'Act#0',
                'start':      '2013-03-01T00:00:00',
                'end':        '2013-03-01T00:00:00',
                'allDay':     False,
                'calendar':   cal.id,
                'color':      f'#{cal.color}',
                'url':        build_popup_url(act0),
                'editable':   True,
                'busy':       False,
                'type':       _('Phone call'),
            },
            data[2],
        )
        self.assertEqual(act4.id, data[3]['id'])

    @skipIfCustomActivity
    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=False)
    def test_activities_data__multiple_users__private_default(self):
        "2 Users, 2 Calendars, Unavailability."
        user = self.login_as_root_and_get()
        other_user = self.create_user()

        cal1 = Calendar.objects.get_default_calendar(user)
        cal2 = Calendar.objects.get_default_calendar(other_user)
        cal3 = Calendar.objects.create(
            user=other_user, name='Cal #3',
            is_custom=True, is_default=False, is_public=True,
        )
        self.assertFalse(cal2.is_public)

        start = self.create_datetime(year=2013, month=4, day=1)

        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_MEETING)
        create = partial(
            Activity.objects.create,
            user=user, type_id=sub_type.type_id, sub_type=sub_type,
        )
        act1 = create(
            title='Act#1', start=start + timedelta(days=1), end=start + timedelta(days=2),
        )
        # Not in [cal1, cal3]
        act2 = create(
            title='Act#2', start=start + timedelta(days=1), end=start + timedelta(days=2),
        )
        # Start KO
        act3 = create(
            title='Act#3', start=start + timedelta(days=32), end=start + timedelta(days=33),
        )
        act4 = create(
            title='Act#4', start=start + timedelta(days=29), end=start + timedelta(days=30),
        )

        act1.calendars.set([cal1])
        act2.calendars.set([cal2])
        act3.calendars.set([cal3])
        act4.calendars.set([cal3])

        unav_stype = self._get_sub_type(constants.UUID_SUBTYPE_UNAVAILABILITY)
        create_unav = partial(
            Activity.objects.create,
            user=user, type_id=unav_stype.type_id, sub_type=unav_stype,
        )
        act6 = create_unav(
            title='Ind#1', start=start + timedelta(days=5), end=start + timedelta(days=6),
        )
        # Not linked
        create_unav(
            title='Ind#2', start=start + timedelta(days=7), end=start + timedelta(days=8),
        )
        act8 = create_unav(
            title='Ind#3', start=start + timedelta(days=9), end=start + timedelta(days=10),
        )

        create_rel = partial(
            Relation.objects.create,
            user=user, type_id=constants.REL_SUB_PART_2_ACTIVITY,
        )
        create_rel(subject_entity=other_user.linked_contact, object_entity=act6)
        create_rel(subject_entity=user.linked_contact,       object_entity=act8)

        # cal2 should not be used, it does not belong to user (so, no 'act2')
        response = self._get_cal_activities([cal1, cal2], start=start.isoformat())

        data = response.json()

        expected = [act1]
        expected_ids  = {act.id for act in expected}
        retrieved_ids = {d['id'] for d in data}
        self.assertEqual(
            expected_ids, retrieved_ids,
            '{} != {} (id map: {})'.format(
                expected_ids, retrieved_ids,
                [f'{act.id} -> {act.title}' for act in expected],
            ),
        )

    @skipIfCustomActivity
    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=True)
    def test_activities_data__multiple_users__public_default(self):
        "Activity in several Calendars."
        user = self.login_as_root_and_get()
        other_user = self.create_user()

        cal1 = Calendar.objects.get_default_calendar(user)
        cal2 = Calendar.objects.get_default_calendar(other_user)

        start = self.create_datetime(year=2013, month=4, day=1)

        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_PHONECALL_OUTGOING)
        create = partial(
            Activity.objects.create,
            user=user,
            type_id=sub_type.type_id,
            sub_type=sub_type,
        )
        act1 = create(
            title='Act#1', start=start + timedelta(days=1),  end=start + timedelta(days=2),
        )
        act2 = create(
            title='Act#2', start=start + timedelta(days=2),  end=start + timedelta(days=3),
        )

        act1.calendars.set([cal1, cal2])  # <== Act1 must be returned twice
        act2.calendars.set([cal2])

        response = self._get_cal_activities([cal1, cal2], start=start.isoformat())
        self.assertCountEqual(
            [
                (act1.id, cal1.id),
                (act1.id, cal2.id),
                (act2.id, cal2.id),
            ],
            [(d['id'], d['calendar']) for d in response.json()],
        )

    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=False)
    def test_selected_calendars_in_session(self):
        user = self.login_as_root_and_get()
        other_user = self.create_user()

        session_before = self.get_alone_element(self._get_user_sessions(user))
        self.assertNotIn('activities__calendars', session_before)

        cal1 = Calendar.objects.get_default_calendar(user)
        cal2 = Calendar.objects.get_default_calendar(other_user)
        cal3 = Calendar.objects.create(
            user=other_user, name='Cal #3',
            is_custom=True, is_default=False, is_public=True,
        )
        Calendar.objects.create(
            user=user, name='Cal #4',
            is_custom=True, is_default=False, is_public=True,
        )
        self.assertFalse(cal2.is_public)  # Ignored

        self._get_cal_activities(
            [cal1, cal2, cal3],
            start=self.create_datetime(year=2019, month=5, day=1).isoformat(),
        )

        # Getting the view again => use Calendars in session
        response = self.assertGET200(self.CALENDAR_URL)
        get_ctxt = response.context.get
        self.assertCountEqual(
            [cal1],
            Calendar.objects.filter(id__in=get_ctxt('my_selected_calendar_ids')),
        )
        self.assertCountEqual(
            [cal3],
            Calendar.objects.filter(id__in=get_ctxt('others_selected_calendar_ids')),
        )

        session_after = self.get_alone_element(self._get_user_sessions(user))
        self.assertCountEqual(
            [cal1.id, cal3.id],
            session_after['activities__calendars'],
        )

    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=True)
    def test_calendars_select(self):
        user = self.login_as_root_and_get()
        other_user = self.create_user()

        session1 = self.get_alone_element(self._get_user_sessions(user))
        self.assertNotIn('activities__calendars', session1)

        cal1 = Calendar.objects.get_default_calendar(user)
        cal2 = Calendar.objects.get_default_calendar(other_user)
        cal3 = Calendar.objects.create(
            user=other_user, name='Cal #3',
            is_custom=True, is_default=False, is_public=False,
        )

        url = reverse('activities__select_calendars')
        self.assertGET405(url)

        self.assertPOST200(url, data={'add': [str(cal1.id), str(cal2.id)]})
        session2 = self.get_alone_element(self._get_user_sessions(user))
        self.assertCountEqual(
            [cal1.id, cal2.id], session2['activities__calendars'],
        )

        # Ignore other not-public Calendars
        self.assertPOST200(url, data={'add': [str(c.id) for c in (cal1, cal2, cal3)]})
        self.assertCountEqual(
            [cal1.id, cal2.id],
            self._get_user_sessions(user)[0]['activities__calendars'],
        )

        # Remove
        self.assertPOST200(url, data={'remove': [str(cal1.id), str(cal3.id)]})
        self.assertCountEqual(
            [cal2.id],
            self._get_user_sessions(user)[0]['activities__calendars'],
        )

    @skipIfCustomActivity
    def test_update_activity_date(self):
        user = self.login_as_root_and_get()

        start = self.create_datetime(year=2013, month=4, day=1, hour=9)
        end   = start + timedelta(hours=2)
        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_OTHER)
        act = Activity.objects.create(
            user=user, title='Act#1',
            type_id=sub_type.type_id, sub_type=sub_type,
            start=start, end=end,
            # floating_type=constants.FLOATING,
            floating_type=Activity.FloatingType.FLOATING,
        )

        url = self.UPDATE_URL
        self.assertGET405(url)

        offset = timedelta(days=1, hours=2)
        new_start = start + offset
        new_end   = end + offset
        self.assertPOST404(url, data={'id': act.id})
        self.assertPOST200(
            url,
            data={
                'id':    act.id,
                'start': new_start.isoformat(),
                'end':   new_end.isoformat(),
            },
        )

        act = self.refresh(act)
        self.assertEqual(new_start, act.start)
        self.assertEqual(new_end,   act.end)
        self.assertEqual(Activity.FloatingType.NARROW, act.floating_type)

    @skipIfCustomActivity
    def test_update_activity_date__collision(self):
        user = self.login_as_root_and_get()
        contact = user.linked_contact

        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_OTHER)
        create_act = partial(
            Activity.objects.create, user=user, busy=True,
            type_id=sub_type.type_id, sub_type=sub_type,
        )
        create_dt = self.create_datetime
        act1 = create_act(
            title='Act#1',
            start=create_dt(year=2013, month=4, day=1, hour=9),
            end=create_dt(year=2013,   month=4, day=1, hour=10),
        )
        act2 = create_act(
            title='Act#2',
            start=create_dt(year=2013, month=4, day=2, hour=9),
            end=create_dt(year=2013,   month=4, day=2, hour=10),
        )

        create_rel = partial(
            Relation.objects.create,
            user=user, type_id=constants.REL_SUB_PART_2_ACTIVITY,
        )
        create_rel(subject_entity=contact, object_entity=act1)
        create_rel(subject_entity=contact, object_entity=act2)

        self.assertPOST(
            409, self.UPDATE_URL,
            data={
                'id':    act1.id,
                'start': act2.start.isoformat(),
                'end':   act2.end.isoformat(),
            },
        )

    @skipIfCustomActivity
    def test_update_activity_date__all_day(self):
        user = self.login_as_root_and_get()

        start = self.create_datetime(year=2013, month=4, day=1, hour=9)
        end   = start + timedelta(hours=2)
        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_OTHER)
        act = Activity.objects.create(
            user=user, title='Act#1', start=start, end=end,
            type_id=sub_type.type_id, sub_type=sub_type,
        )

        url = self.UPDATE_URL
        self.assertPOST404(url, data={'id': act.id})
        self.assertPOST200(
            url,
            data={
                'id':     act.id,
                'start':  start.isoformat(),
                'end':    end.isoformat(),
                'allDay': '1',
            },
        )

        act = self.refresh(act)
        create_dt = partial(self.create_datetime, year=2013, month=4, day=1)
        self.assertEqual(create_dt(hour=0),             act.start)
        self.assertEqual(create_dt(hour=23, minute=59), act.end)


class UserCalendarCreationTestCase(_ActivitiesTestCase):
    CREATION_URL = reverse('activities__create_calendar')

    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=None)
    def test_first_calendar(self):
        user = self.login_as_super()
        self.assertFalse(Calendar.objects.filter(is_default=True, user=user))

        url = self.CREATION_URL
        context = self.assertGET200(url).context
        self.assertEqual(_('Create a calendar'), context.get('title'))
        self.assertEqual(_('Save the calendar'), context.get('submit_label'))

        name = 'My pretty calendar'
        color = '009900'
        self.assertNoFormError(self.client.post(
            url, data={'name':  name, 'color': color},
        ))

        cal = self.get_alone_element(Calendar.objects.filter(user=user))
        self.assertEqual(name, cal.name)
        self.assertEqual(color, cal.color)
        self.assertIs(cal.is_default, True)
        self.assertIs(cal.is_public, False)
        self.assertIs(cal.is_custom, True)

    def test_new_default(self):
        user = self.login_as_activities_user()
        cal1 = Calendar.objects.get_default_calendar(user)

        name = 'My pretty calendar'
        self.assertNoFormError(self.client.post(
            self.CREATION_URL,
            data={
                'name': name,
                'is_default': True,
                'is_public': True,
                'color': 'FF0000',
            },
        ))

        cal2 = self.get_object_or_fail(Calendar, name=name)
        self.assertTrue(cal2.is_default)
        self.assertTrue(cal2.is_public)
        self.assertFalse(self.refresh(cal1).is_default)

    def test_forbidden(self):
        self.login_as_standard(allowed_apps=['persons'])
        self.assertGET403(self.CREATION_URL)


class UserCalendarEditionTestCase(_ActivitiesTestCase):
    def test_super_user(self):
        user = self.login_as_root_and_get()
        cal = Calendar.objects.get_default_calendar(user)
        url = reverse('activities__edit_calendar', args=(cal.id,))
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')
        self.assertEqual(_('Edit «{object}»').format(object=cal), response.context.get('title'))

        # ---
        name = 'My calendar'
        color = '0000FF'
        self.assertNoFormError(self.client.post(
            url, data={'name': name, 'color': color},
        ))

        cal = self.refresh(cal)
        self.assertEqual(name,  cal.name)
        self.assertEqual(color, cal.color)

    def test_other_user(self):
        "Edit calendar of another user."
        self.login_as_root()
        cal = Calendar.objects.get_default_calendar(self.create_user())
        self.assertGET403(reverse('activities__edit_calendar', args=(cal.id,)))

    def test_regular_user(self):
        user = self.login_as_activities_user()
        cal = Calendar.objects.get_default_calendar(user)
        self.assertGET200(reverse('activities__edit_calendar', args=(cal.id,)))

    def test_app_perms(self):
        "App credentials needed."
        user = self.login_as_standard(allowed_apps=['persons'])  # 'activities'
        cal = Calendar.objects.get_default_calendar(user)
        self.assertGET403(reverse('activities__edit_calendar', args=(cal.id,)))


class UserCalendarDeletionTestCase(_ActivitiesTestCase):
    @staticmethod
    def _build_delete_calendar_url(calendar):
        return reverse('activities__delete_calendar', args=(calendar.id,))

    def test_not_custom(self):
        "Not custom -> error."
        user = self.login_as_root_and_get()
        self.assertGET404(reverse('activities__delete_calendar', args=(self.UNUSED_PK,)))

        Calendar.objects.get_default_calendar(user)
        cal = Calendar.objects.create(user=user, name='Cal #1', is_custom=False)
        self.assertContains(
            self.client.get(self._build_delete_calendar_url(cal)),
            _('You cannot delete this calendar: it is not custom.'),
            status_code=409,
            html=True,
        )
        self.get_object_or_fail(Calendar, pk=cal.pk)

    def test_custom(self):
        user = self.login_as_root_and_get()

        def_cal = Calendar.objects.get_default_calendar(user)
        cal = Calendar.objects.create(user=user, name='Cal #1', is_custom=True)

        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_OTHER)
        act = Activity.objects.create(
            user=user, title='Act#1',
            type_id=sub_type.type_id, sub_type=sub_type,
        )
        act.calendars.add(cal)

        url = self._build_delete_calendar_url(cal)

        # GET ---
        response = self.assertGET200(url)

        context = response.context
        self.assertEqual(
            _('Replace & delete «{object}»').format(object=cal),
            context.get('title'),
        )

        fname = 'replace_activities__activity_calendars'
        with self.assertNoException():
            replace_field = context['form'].fields[fname]

        self.assertEqual(
            f'{_("Activity")} - {_("Calendars")}', replace_field.label,
        )
        self.assertListEqual(
            [(def_cal.id, str(def_cal))], [*replace_field.choices],
        )

        # POST ---
        self.assertNoFormError(self.client.post(
            url, data={'replace_activities__activity_calendars': def_cal.id},
        ))

        dcom = self.get_object_or_fail(
            DeletionCommand,
            content_type=ContentType.objects.get_for_model(Calendar),
        )
        self.assertEqual(cal, dcom.instance_to_delete)
        self.assertListEqual(
            [('fixed_value', Activity, 'calendars', def_cal)],
            [
                (r.type_id, r.model_field.model, r.model_field.name, r.get_value())
                for r in dcom.replacers
            ],
        )

        deletor_type.execute(dcom.job)
        self.assertDoesNotExist(cal)
        self.assertIn(def_cal, [*act.calendars.all()])

    def test_regular_user(self):
        user = self.login_as_activities_user()

        def_cal = Calendar.objects.get_default_calendar(user)
        cal = Calendar.objects.create(user=user, name='Cal #1', is_custom=True)

        self.assertNoFormError(self.client.post(
            self._build_delete_calendar_url(cal),
            data={'replace_activities__activity_calendars': def_cal.id},
        ))

        self.get_object_or_fail(
            DeletionCommand,
            content_type=ContentType.objects.get_for_model(Calendar),
        )

    def test_other_user(self):
        "Other user's calendar."
        self.login_as_activities_user()
        other_user = self.get_root_user()

        Calendar.objects.get_default_calendar(other_user)
        cal = Calendar.objects.create(user=other_user, name='Cal #1', is_custom=True)
        self.assertContains(
            self.client.get(self._build_delete_calendar_url(cal)),
            _('You are not allowed to delete this calendar.'),
            status_code=403,
            html=True,
        )

    def test_last_calendar(self):
        "The deleted calendar is the last one (but custom -- should not happen btw)."
        user = self.login_as_root_and_get()

        cal = Calendar.objects.get_default_calendar(user)
        Calendar.objects.filter(id=cal.id).update(is_custom=True)
        self.assertGET409(self._build_delete_calendar_url(cal))

    def test_deletion_command_uniqueness(self):
        user = self.login_as_root_and_get()
        self.assertFalse(DeletionCommand.objects.first())

        Calendar.objects.get_default_calendar(user)
        cal2 = Calendar.objects.create(user=user, name='Cal #2')
        cal3 = Calendar.objects.create(user=user, name='Cal #3')

        job = Job.objects.create(type_id=deletor_type.id, user=user)
        self.assertEqual(Job.STATUS_WAIT, job.status)

        dcom = DeletionCommand.objects.create(
            content_type=Calendar,
            job=job,
            pk_to_delete=str(cal2.pk),
            deleted_repr=str(cal2),
        )

        url = self._build_delete_calendar_url(cal3)
        msg = _(
            'A deletion process for an instance of «{model}» already exists.'
        ).format(model=_('Calendar'))
        self.assertContains(self.client.get(url), msg, status_code=409)

        # ---
        job.status = Job.STATUS_ERROR
        job.save()
        self.assertContains(self.client.get(url), msg, status_code=409)

        # ---
        job.status = Job.STATUS_OK
        job.save()
        response = self.assertGET200(url)
        self.assertIn('form', response.context)
        self.assertDoesNotExist(job)
        self.assertDoesNotExist(dcom)


class CalendarLinkingTestCase(_ActivitiesTestCase):
    @staticmethod
    def _build_link_url(activity_id):
        return reverse('activities__link_calendar', args=(activity_id,))

    @skipIfCustomActivity
    def test_change_activity_calendar(self):
        "Reassign activity calendar."
        user = self.login_as_root_and_get()
        default_calendar = Calendar.objects.get_default_calendar(user)

        cal = Calendar.objects.create(user=user, name='Cal #1', is_custom=True)
        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_NETWORK)
        activity = Activity.objects.create(
            user=user, title='Act#1',
            type_id=sub_type.type_id, sub_type=sub_type,
        )
        activity.calendars.add(default_calendar)
        self.assertListEqual([default_calendar], [*activity.calendars.all()])

        activity_url = activity.get_absolute_url()
        response = self.assertGET200(activity_url)
        self.assertContains(response, escape(default_calendar.name))

        url = self._build_link_url(activity.id)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')
        self.assertEqual(
            _('Change calendar of «{object}»').format(object=activity),
            response.context.get('title'),
        )

        response = self.assertPOST200(url, data={'calendar': cal.id})
        self.assertNoFormError(response)

        activity = self.refresh(activity)
        self.assertListEqual([cal], [*activity.calendars.all()])

        response = self.assertGET200(activity_url)
        self.assertContains(response, cal.name)

    @skipIfCustomActivity
    def test_multiple_calendars(self):
        "Multiple calendars => error (waiting the right solution)."
        user = self.login_as_root_and_get()
        default_calendar = Calendar.objects.get_default_calendar(user)

        create_cal = partial(Calendar.objects.create, user=user, is_custom=True)
        cal1 = create_cal(name='Cal #1')
        cal2 = create_cal(name='Cal #2')

        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_QUALIFICATION)
        act = Activity.objects.create(
            user=user, title='Act#1',
            type_id=sub_type.type_id, sub_type=sub_type,
        )
        act.calendars.set([default_calendar, cal1])

        url = self._build_link_url(act.id)
        self.assertGET409(url)
        self.assertPOST409(url, data={'calendar': cal2.id})

    @skipIfCustomActivity
    def test_own_calendar(self):
        "Credentials: user can always change its calendars."
        user = self.login_as_activities_user()
        self.add_credentials(user.role, all=['VIEW'], own='*')

        default_calendar = Calendar.objects.get_default_calendar(user)
        cal = Calendar.objects.create(user=user, name='Cal #1', is_custom=True)

        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_PHONECALL_CONFERENCE)
        act = Activity.objects.create(
            user=self.get_root_user(), title='Act#1',
            type_id=sub_type.type_id, sub_type=sub_type,
        )
        self.assertFalse(user.has_perm_to_change(act))
        self.assertFalse(user.has_perm_to_link(act))

        act.calendars.add(default_calendar)

        url = self._build_link_url(act.id)
        self.assertGET200(url)
        self.assertNoFormError(self.assertPOST200(url, data={'calendar': cal.id}))
        self.assertListEqual([cal], [*act.calendars.all()])

    def test_app_perms(self):
        "App credentials needed."
        user = self.login_as_standard(allowed_apps=['creme_core'])
        self.add_credentials(user.role, all=['VIEW', 'CHANGE', 'LINK'])

        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_OTHER)
        act = Activity.objects.create(
            user=self.get_root_user(), title='Act#1',
            type_id=sub_type.type_id, sub_type=sub_type,
        )
        act.calendars.add(Calendar.objects.get_default_calendar(user))
        self.assertGET403(self._build_link_url(act.id))


class CremeConfigViewsTestCase(BrickTestCaseMixin, _ActivitiesTestCase):
    CONF_ADD_URL = reverse(
        'creme_config__create_instance', args=('activities', 'calendar'),
    )

    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=None)
    def test_creation(self):
        user = self.login_as_super()
        staff = self.create_user(index=1, is_staff=True)

        self.assertGET200(reverse('creme_config__app_portal', args=('activities',)))

        cal_portal = self.assertGET200(
            reverse('creme_config__model_portal', args=('activities', 'calendar'))
        )
        brick_node = self.get_brick_node(
            self.get_html_tree(cal_portal.content), brick=CalendarsBrick,
        )
        user_names = {
            div.text for div in brick_node.findall(
                './/div[@class="calendar-config-group-title"]'
            )
        }
        self.assertIn(str(user), user_names)
        self.assertIn(str(self.get_root_user()), user_names)
        self.assertNotIn(str(staff), user_names)

        # ---
        url = self.CONF_ADD_URL
        self.assertGET200(url)

        name = 'My Cal'
        color = '998877'
        self.assertNoFormError(self.client.post(
            url,
            data={
                'name': name,
                'user': user.id,
                'color': color,
            },
        ))

        cal = self.get_object_or_fail(Calendar, name=name, user=user)
        self.assertEqual(color, cal.color)
        self.assertTrue(cal.is_default)
        self.assertTrue(cal.is_custom)
        self.assertFalse(cal.is_public)

        now_value = now()
        self.assertDatetimesAlmostEqual(cal.created, now_value)
        self.assertDatetimesAlmostEqual(cal.modified, now_value)

    def test_creation__new_default(self):
        "Only one default."
        user = self.login_as_root_and_get()
        cal1 = Calendar.objects.get_default_calendar(user)

        name = 'My default Cal'
        self.assertNoFormError(self.client.post(
            self.CONF_ADD_URL,
            data={
                'name': name,
                'user': user.id,
                'is_default': True,
                'is_public': True,
                'color': '0000FF',
            },
        ))

        cal2 = self.get_object_or_fail(Calendar, name=name, user=user)
        self.assertTrue(cal2.is_default)
        self.assertTrue(cal2.is_custom)
        self.assertTrue(cal2.is_public)

        self.assertFalse(self.refresh(cal1).is_default)

    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=None)
    def test_creation__team(self):
        user = self.login_as_root_and_get()

        team = self.create_team('Roots', user)
        self.assertFalse(Calendar.objects.filter(user=team))

        url = self.CONF_ADD_URL
        name = 'Team calendar'
        color = '008800'
        self.assertNoFormError(self.client.post(
            url,
            data={
                'name': name,
                'color': color,
                'user': team.id,
                'is_default': True,
                'is_public': False,  # <== True will be forced
            },
        ))

        cal = self.get_object_or_fail(Calendar, user=team)
        self.assertEqual(name, cal.name)
        self.assertEqual(color, cal.color)
        self.assertIs(cal.is_default, True)
        self.assertIs(cal.is_custom, True)
        self.assertIs(cal.is_public, True)

        # Cannot create a second one ---
        response2 = self.assertPOST200(
            url,
            data={
                'name': 'Team calendar #2',
                'color': '000088',
                'user': team.id,
                'is_default': True,
                # 'is_public': False,  # <== True will be forced
            },
        )
        self.assertFormError(
            response2.context['form'],
            field='user',
            errors=_(
                'Select a valid choice. That choice is not one of the available choices.'
            ),
        )

    def test_creation__inactive_user(self):
        self.login_as_root()
        inactive_user = self.create_user(is_active=False)
        response = self.assertPOST200(
            self.CONF_ADD_URL,
            data={
                'name': 'Inactive calendar',
                'color': '000088',
                'user': inactive_user.id,
                'is_default': True,
            },
        )
        self.assertFormError(
            response.context['form'],
            field='user',
            errors=_(
                'Select a valid choice. That choice is not one of the available choices.'
            ),
        )

    def test_edition(self):
        user = self.login_as_root_and_get()
        cal1 = Calendar.objects.get_default_calendar(user)

        name = 'cal#1'
        cal2 = Calendar.objects.create(user=user, name=name)

        url = reverse(
            'creme_config__edit_instance',
            args=('activities', 'calendar', cal2.id),
        )
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertNotIn('user', fields)

        name = name.title()
        color = '0000FF'
        self.assertNoFormError(self.client.post(
            url,
            data={
                'name': name,
                'is_default': True,
                'is_public': True,
                'color': color,
            },
        ))

        cal2 = self.refresh(cal2)
        self.assertEqual(name,  cal2.name)
        self.assertEqual(color, cal2.color)
        self.assertTrue(cal2.is_default)
        self.assertTrue(cal2.is_public)

        self.assertFalse(self.refresh(cal1).is_default)

    def test_deletion(self):
        def get_url(cal):
            return reverse(
                'creme_config__delete_instance',
                args=('activities', 'calendar', cal.id),
            )

        user = self.login_as_root_and_get()
        other_user = self.create_user()

        cal1 = Calendar.objects.get_default_calendar(user)
        cal2 = Calendar.objects.create(
            user=user, name='Cal#2', is_custom=False,
        )
        self.assertGET409(get_url(cal2))  # Cannot deleted a not custom Calendar

        cal3 = Calendar.objects.create(user=user, name='Cal#3')
        Calendar.objects.get_default_calendar(other_user)  # Not in choices

        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_OTHER)
        act = Activity.objects.create(
            user=user, title='Act#1',
            type_id=sub_type.type_id, sub_type=sub_type,
        )
        act.calendars.add(cal3)

        # GET ---
        url = get_url(cal3)
        response = self.assertGET200(url)

        context = response.context
        self.assertEqual(
            _('Replace & delete «{object}»').format(object=cal3),
            context.get('title')
        )

        fname = 'replace_activities__activity_calendars'
        with self.assertNoException():
            replace_field = context['form'].fields[fname]

        self.assertEqual(
            '{} - {}'.format(_('Activity'), _('Calendars')),
            replace_field.label
        )
        self.assertEqual(
            _('The activities on the deleted calendar will be moved to the selected one.'),
            replace_field.help_text,
        )
        self.assertCountEqual(
            [(cal1.id, str(cal1)), (cal2.id, str(cal2))],
            [*replace_field.choices],
        )

        # POST ---
        response = self.client.post(
            url, data={'replace_activities__activity_calendars': cal2.id},
        )
        self.assertNoFormError(response)

        dcom = self.get_object_or_fail(
            DeletionCommand,
            content_type=ContentType.objects.get_for_model(Calendar),
        )
        self.assertEqual(cal3, dcom.instance_to_delete)
        self.assertListEqual(
            [('fixed_value', Activity, 'calendars', cal2)],
            [
                (r.type_id, r.model_field.model, r.model_field.name, r.get_value())
                for r in dcom.replacers
            ],
        )
        self.assertEqual(1, dcom.total_count)

        job = dcom.job
        self.assertListEqual(
            [
                _('Deleting «{object}» ({model})').format(
                    object=cal3.name, model=_('Calendar'),
                ),
                _('In «{model} - {field}», replace by «{new}»').format(
                    model=_('Activity'),
                    field=_('Calendars'),
                    new=cal2,
                ),
            ],
            deletor_type.get_description(job),
        )

        deletor_type.execute(job)
        self.assertDoesNotExist(cal3)
        self.assertIn(cal2, [*act.calendars.all()])

    def test_staff(self):
        user = self.login_as_super(is_staff=True)

        response = self.assertGET200(
            reverse('creme_config__model_portal', args=('activities', 'calendar'))
        )
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=CalendarsBrick,
        )
        user_names = {
            div.text for div in brick_node.findall(
                './/div[@class="calendar-config-group-title"]'
            )
        }
        self.assertIn(str(user), user_names)
        self.assertIn(str(self.get_root_user()), user_names)
