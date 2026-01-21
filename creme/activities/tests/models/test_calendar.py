from uuid import UUID

from django.core.exceptions import ValidationError
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.activities.models import Calendar

from ..base import _ActivitiesTestCase


class CalendarManagerTestCase(_ActivitiesTestCase):
    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=None)
    def test_create_default_calendar(self):
        user = self.create_user()
        self.assertFalse(Calendar.objects.filter(user=user))

        cal1 = Calendar.objects.create_default_calendar(user=user)
        self.assertEqual(_("{user}'s calendar").format(user=user), cal1.name)
        self.assertTrue(cal1.is_default)
        self.assertFalse(cal1.is_custom)
        self.assertFalse(cal1.is_public)
        self.assertTrue(cal1.color)
        self.assertIsInstance(cal1.uuid, UUID)

        name2 = 'Default'
        color2 = '0f0f0f'
        cal2 = Calendar.objects.create_default_calendar(
            user=user, name=name2, is_public=True, color=color2,
        )
        self.assertEqual(name2, cal2.name)
        self.assertTrue(cal2.is_default)
        self.assertFalse(cal2.is_custom)
        self.assertTrue(cal2.is_public)
        self.assertEqual(color2, cal2.color)

        # default not checked (<check_for_default=False>)
        self.assertTrue(self.refresh(cal1).is_default)

        cal3 = Calendar.objects.create_default_calendar(user=user, check_for_default=True)
        self.assertTrue(cal3.is_default)
        self.assertFalse(self.refresh(cal1).is_default)
        self.assertFalse(self.refresh(cal2).is_default)

    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=None)
    def test_get_default_calendar(self):
        user = self.create_user()
        self.assertFalse(Calendar.objects.filter(user=user))

        with self.assertNumQueries(2):
            def_cal = Calendar.objects.get_default_calendar(user)

        self.assertEqual(_("{user}'s calendar").format(user=user), def_cal.name)
        self.assertTrue(def_cal.color)

        def_cal2 = self.assertUserHasDefaultCalendar(user)
        self.assertEqual(def_cal, def_cal2)

    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=None)
    def test_get_default_calendar__already_exists(self):
        "Default already exists."
        user = self.create_user()

        cal1 = Calendar.objects.create(is_default=True, user=user)

        with self.assertNumQueries(1):
            def_cal = Calendar.objects.get_default_calendar(user)

        self.assertEqual(cal1, def_cal)

    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=None)
    def test_get_default_calendar__several_default(self):
        "There are several default calendars."
        user = self.create_user()
        cal1 = Calendar.objects.create(is_default=True, user=user, name='Cal#1')
        cal2 = Calendar.objects.create(user=user, name='Cal#2')
        Calendar.objects.filter(id=cal2.id).update(is_default=True)

        # Be sure that we well managed the automatic save() behaviour
        self.assertEqual(2, Calendar.objects.filter(is_default=True, user=user).count())

        self.assertEqual(cal1, Calendar.objects.get_default_calendar(user))
        self.assertFalse(self.refresh(cal2).is_default)

    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=None)
    def test_get_default_calendar__no_default(self):
        "No default Calendar in existing ones."
        user = self.create_user()
        cal = Calendar.objects.create(user=user, name='Cal #1')
        Calendar.objects.filter(id=cal.id).update(is_default=False)

        # Be sure that we well managed the automatic save() behaviour
        self.assertFalse(Calendar.objects.filter(is_default=True, user=user))

        with self.assertNumQueries(2):
            def_cal = Calendar.objects.get_default_calendar(user)

        self.assertEqual(cal, def_cal)
        self.assertTrue(def_cal.is_default)

    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=True)
    def test_get_default_calendars(self):
        user1 = self.create_user(index=0)
        user2 = self.create_user(index=1)

        def_cal1 = self.assertUserHasDefaultCalendar(user1)
        def_cal2 = self.assertUserHasDefaultCalendar(user2)

        with self.assertNumQueries(1):
            calendars = Calendar.objects.get_default_calendars([user1, user2])

        self.assertDictEqual(
            {
                user1.id: def_cal1,
                user2.id: def_cal2,
            },
            calendars,
        )

    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=None)
    def test_get_default_calendars__no_calendar(self):
        user1 = self.create_user(index=0)
        user2 = self.create_user(index=1)

        self.assertFalse(Calendar.objects.filter(user__in=[user1, user2]))

        with self.assertNumQueries(3):
            calendars = Calendar.objects.get_default_calendars([user1, user2])

        def_cal1 = self.assertUserHasDefaultCalendar(user1)
        def_cal2 = self.assertUserHasDefaultCalendar(user2)

        self.assertDictEqual(
            {
                user1.id: def_cal1,
                user2.id: def_cal2,
            },
            calendars,
        )

    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=True)
    def test_get_default_calendars__no_default(self):
        "No default Calendar in existing ones."
        user1 = self.create_user(index=0)
        user2 = self.create_user(index=1)

        def_cal1 = self.assertUserHasDefaultCalendar(user1)
        def_cal2 = self.assertUserHasDefaultCalendar(user2)

        Calendar.objects.filter(id__in=[def_cal1.id, def_cal2.id]).update(is_default=False)

        # Be sure that we well managed the automatic save() behaviour
        self.assertFalse(Calendar.objects.filter(is_default=True, user=user1))

        with self.assertNumQueries(2):
            calendars = Calendar.objects.get_default_calendars([user1, user2])

        self.assertDictEqual(
            {
                user1.id: def_cal1,
                user2.id: def_cal2,
            },
            calendars,
        )
        self.assertTrue(self.refresh(def_cal1).is_default)
        self.assertTrue(self.refresh(def_cal2).is_default)

    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=None)
    def test_get_default_calendars__no_user(self):
        with self.assertNumQueries(0):
            Calendar.objects.get_default_calendars([])

    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=None)
    def test_get_default_calendars__several_default(self):
        "There are several default calendars."
        user = self.create_user()
        cal1 = Calendar.objects.create(is_default=True, user=user, name='Cal#1')
        cal2 = Calendar.objects.create(user=user, name='Cal#2')
        Calendar.objects.filter(id=cal2.id).update(is_default=True)

        # Be sure that we well managed the automatic save() behaviour
        self.assertEqual(2, Calendar.objects.filter(is_default=True, user=user).count())

        with self.assertNumQueries(2):
            calendars = Calendar.objects.get_default_calendars([user])

        self.assertDictEqual({user.id: cal1}, calendars)
        self.assertTrue(self.refresh(cal1).is_default)
        self.assertFalse(self.refresh(cal2).is_default)


class CalendarTestCase(_ActivitiesTestCase):
    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=None)
    def test_user_default_calendar_auto__none(self):
        user = self.create_user()
        self.assertFalse(Calendar.objects.filter(user=user))

    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=True)
    def test_user_default_calendar_auto__public(self):
        user = self.create_user()

        calendar = self.get_object_or_fail(Calendar, user=user)
        self.assertEqual(_("{user}'s calendar").format(user=user), calendar.name)
        self.assertTrue(calendar.is_default)
        self.assertFalse(calendar.is_custom)
        self.assertTrue(calendar.is_public)

    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=False)
    def test_user_default_calendar_auto__private(self):
        "Private calendar."
        user = self.create_user()

        calendar = self.get_object_or_fail(Calendar, user=user)
        self.assertEqual(_("{user}'s calendar").format(user=user), calendar.name)
        self.assertTrue(calendar.is_default)
        self.assertFalse(calendar.is_custom)
        self.assertFalse(calendar.is_public)

    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=True)
    def test_user_default_calendar_auto__staff(self):
        "Staff user => no calendar."
        user = self.create_user(is_staff=True)
        self.assertFalse(Calendar.objects.filter(user=user))

    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=True)
    def test_user_default_calendar_auto__inactive(self):
        "Inactive user => no calendar."
        user = self.create_user(is_active=False)
        self.assertFalse(Calendar.objects.filter(user=user))

    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=False)
    def test_user_default_calendar_auto__team(self):
        user = self.get_root_user()

        team = self.create_team('Roots', user)
        calendar = self.get_object_or_fail(Calendar, user=team)
        self.assertEqual(_("{user}'s calendar").format(user=team), calendar.name)
        self.assertTrue(calendar.is_default)
        self.assertFalse(calendar.is_custom)
        self.assertTrue(calendar.is_public)  # <= forced

    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=True)
    def test_save(self):
        "Save() + update_fields."
        user = self.create_user()

        calendar1 = self.get_object_or_fail(Calendar, user=user)
        self.assertTrue(calendar1.is_default)

        calendar2 = Calendar.objects.create(user=user, name='Calendar 2')
        self.assertFalse(calendar2.is_default)

        # You should not do this, because there is a moment with no default calendar
        Calendar.objects.filter(id=calendar1.id).update(is_default=False)

        calendar2.name = name2 = 'Other calendar'
        calendar2.save(update_fields=['name'])

        calendar2.refresh_from_db()
        self.assertEqual(name2, calendar2.name)
        self.assertTrue(calendar2.is_default)

        self.assertFalse(self.refresh(calendar1).is_default)

    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=None)
    def test_save__team(self):
        user = self.get_root_user()

        team = self.create_team('Roots', user)
        self.assertFalse(Calendar.objects.filter(user=team))

        name = 'First calendar'
        color = '666666'
        cal = Calendar.objects.create(
            name=name,
            color=color,
            user=team,
            is_default=True,
            is_public=False,  # <== True will be forced
            is_custom=True,
        )
        self.assertEqual(team, cal.user)
        self.assertEqual(name, cal.name)
        self.assertEqual(color, cal.color)
        self.assertIs(cal.is_default, True)
        self.assertIs(cal.is_custom, True)
        self.assertIs(cal.is_public, True)

    @override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=False)
    def test_portable_key(self):
        user = self.create_user()
        calendar = self.get_object_or_fail(Calendar, user=user)

        with self.assertNoException():
            key = calendar.portable_key()
        self.assertIsInstance(key, str)
        self.assertUUIDEqual(calendar.uuid, key)

        # ---
        with self.assertNoException():
            got_calendar = Calendar.objects.get_by_portable_key(key)
        self.assertEqual(calendar, got_calendar)

    def test_color_field(self):
        user = self.login_as_root_and_get()
        cal = Calendar.objects.get_default_calendar(user)

        cal.color = 'FF0000'
        with self.assertNoException():
            cal.full_clean()

        cal.color = 'ZZ0000'
        self.assertRaises(ValidationError, cal.full_clean)

    def test_delete_user(self):
        """The User who receives the Calendars from the deleted User should keep
        his default Calendar.
        """
        user = self.login_as_root_and_get()
        other_user = self.create_user()

        cal11 = Calendar.objects.get_default_calendar(user)
        cal12 = Calendar.objects.create(user=user, name='Cal#12')
        cal21 = Calendar.objects.get_default_calendar(other_user)
        cal22 = Calendar.objects.create(user=other_user, name='Cal#22')
        self.assertTrue(self.refresh(cal11).is_default)
        self.assertFalse(self.refresh(cal12).is_default)
        self.assertTrue(self.refresh(cal21).is_default)
        self.assertFalse(self.refresh(cal22).is_default)

        url = reverse('creme_config__delete_user', args=(other_user.id,))
        self.assertGET200(url)

        self.assertNoFormError(self.client.post(url, {'to_user': user.id}))
        self.assertDoesNotExist(other_user)

        self.assertCountEqual(
            [cal11.id, cal12.id, cal21.id, cal22.id],
            Calendar.objects.filter(user=user).values_list('id', flat=True),
        )
        self.assertTrue(self.refresh(cal11).is_default)
        self.assertFalse(self.refresh(cal12).is_default)
        self.assertFalse(self.refresh(cal21).is_default)
        self.assertFalse(self.refresh(cal22).is_default)
