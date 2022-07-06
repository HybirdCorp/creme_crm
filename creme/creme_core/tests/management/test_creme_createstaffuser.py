from django.core.management import call_command
from django.core.management.base import CommandError

from creme.creme_core.management.commands.creme_createstaffuser import (
    Command as StaffCommand,
)
from creme.creme_core.models import CremeUser

from .. import base


@base.skipIfCustomUser
class CreateStaffUserTestCase(base.CremeTestCase):
    @staticmethod
    def call_command(**kwargs):
        call_command(StaffCommand(), verbosity=0, interactive=False, **kwargs)

    def test_errors(self):
        count = CremeUser.objects.count()

        with self.assertRaises(CommandError):
            self.call_command()

        with self.assertRaises(CommandError):
            self.call_command(username='staff1')

        with self.assertRaises(CommandError):
            self.call_command(username='staff1', first_name='John')

        with self.assertRaises(CommandError):
            self.call_command(
                username='staff1', first_name='John', last_name='Staffman',
            )

        self.assertEqual(count, CremeUser.objects.count())

    def test_ok(self):
        count = CremeUser.objects.count()

        username = 'staff1'
        first_name = 'John'
        last_name = 'Staffman'
        email = 'staffman@acme.com'

        with self.assertNoException():
            self.call_command(
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=email,
            )

        self.assertEqual(count + 1, CremeUser.objects.count())

        user = self.get_object_or_fail(CremeUser, username=username)
        self.assertEqual(first_name, user.first_name)
        self.assertEqual(last_name,  user.last_name)
        self.assertEqual(email,      user.email)
        self.assertIs(user.is_superuser, True)
        self.assertIsNone(user.role)
        self.assertIs(user.is_team, False)
        self.assertIs(user.is_staff, True)
