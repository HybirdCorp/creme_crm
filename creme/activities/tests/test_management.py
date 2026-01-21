from io import StringIO

from django.core.management import call_command
from django.test.utils import override_settings
from parameterized import parameterized

from ..management.commands.activities_create_default_calendars import (
    Command as CalCommand,
)
from ..models import Calendar
from .base import _ActivitiesTestCase


class CreateDefaultCalendarsCommandTestCase(_ActivitiesTestCase):
    @parameterized.expand([
        (
            True,
            0,  # verbosity
            '',  # message
        ),
        (
            False,
            1,  # verbosity
            '2 calendar(s) created.\n',
        ),
    ])
    def test_creation(self, is_public, verbosity, msg):
        with override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=None):
            user1 = self.create_user(index=0)
            user2 = self.create_user(index=1)
            user3 = self.create_user(index=2, is_staff=True)
            user4 = self.create_user(index=3, is_active=False)

        self.assertFalse(Calendar.objects.filter(user__in=[user1, user2, user3, user4]))

        with override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=is_public):
            user5 = self.create_user(
                username='soldat#42', email='soldat42@noir.jp',
                first_name='John', last_name='Doe',
            )
        cal4_1 = self.get_object_or_fail(Calendar, is_default=True, user=user5)
        cal4_2 = Calendar.objects.create(
            name='Private calendar of Chloé',
            is_default=False, user=user5, is_public=False,
        )

        stdout = StringIO()
        stderr = StringIO()

        with override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=is_public):
            call_command(CalCommand(stdout=stdout, stderr=stderr), verbosity=verbosity)

        cal1 = self.get_object_or_fail(Calendar, is_default=True, user=user1)
        self.assertEqual(is_public, cal1.is_public)

        cal2 = self.get_object_or_fail(Calendar, is_default=True, user=user2)
        self.assertEqual(is_public, cal2.is_public)

        self.assertFalse(Calendar.objects.filter(user=user3))
        self.assertFalse(Calendar.objects.filter(user=user4))

        self.assertCountEqual(
            [cal4_1, cal4_2],
            Calendar.objects.filter(user=user5),
        )

        self.assertFalse(stderr.getvalue())
        self.assertEqual(msg, stdout.getvalue())

    @parameterized.expand([
        (
            None,
            'ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC is None => no calendar created.',
        ),
        (
            'invalid',
            'ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC is invalid '
            '(not in {None, True, False}) => no calendar created.',
        ),
    ])
    def test_no_creation(self, is_public, err_msg):
        with override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=None):
            user = self.create_user()

        self.assertFalse(Calendar.objects.filter(user=user))

        stdout0 = StringIO()
        stderr0 = StringIO()

        with override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=is_public):
            call_command(CalCommand(stdout=stdout0, stderr=stderr0), verbosity=0)

        self.assertFalse(Calendar.objects.filter(user=user))
        self.assertFalse(stdout0.getvalue())
        self.assertFalse(stderr0.getvalue())

        # verbosity ---
        stdout1 = StringIO()
        stderr1 = StringIO()

        with override_settings(ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC=is_public):
            call_command(CalCommand(stdout=stdout1, stderr=stderr1), verbosity=1)

        self.assertFalse(Calendar.objects.filter(user=user))
        self.assertFalse(stdout1.getvalue())
        self.assertEqual(f'{err_msg}\n', stderr1.getvalue())
