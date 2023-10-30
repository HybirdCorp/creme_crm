from django.core.management import call_command
from django.core.management.base import CommandError

from creme.creme_core.constants import UUID_CHANNEL_SYSTEM
from creme.creme_core.management.commands.creme_announce import (
    Command as AnnounceCommand,
)
from creme.creme_core.models import Notification
from creme.creme_core.notification import UpgradeAnnouncement

from .. import base


class AnnounceTestCase(base.CremeTestCase):
    @staticmethod
    def call_command(start, **kwargs):
        call_command(AnnounceCommand(), start, verbosity=0, **kwargs)

    def test_ok(self):
        root = self.get_root_user()
        other = self.create_user(index=0)
        staff = self.create_user(index=1, is_staff=True)
        disabled = self.create_user(index=2, is_active=False)

        self.assertFalse(Notification.objects.all())

        with self.assertNoException():
            self.call_command('2023-12-24T23:00')

        notifications = {
            notif.user_id: notif
            for notif in Notification.objects.filter(channel__uuid=UUID_CHANNEL_SYSTEM)
        }
        root_notif = notifications.get(root.id)
        self.assertIsNotNone(root_notif)
        content = root_notif.content
        self.assertIsInstance(content, UpgradeAnnouncement)
        self.assertEqual(
            self.create_datetime(year=2023, month=12, day=24, hour=23),
            content.start,
        )
        self.assertFalse(content.message)

        other_notif = notifications.get(other.id)
        self.assertIsNotNone(other_notif)
        self.assertEqual(UpgradeAnnouncement.id, other_notif.content_id)

        self.assertNotIn(staff.id,    notifications)
        self.assertNotIn(disabled.id, notifications)

    def test_message(self):
        root = self.get_root_user()
        message = 'duration: 2 hours'

        with self.assertNoException():
            self.call_command("2024-02-15T22:30", message=message)

        notif = self.get_object_or_fail(
            Notification, channel__uuid=UUID_CHANNEL_SYSTEM, user=root,
        )
        content = notif.content
        self.assertEqual(
            self.create_datetime(year=2024, month=2, day=15, hour=22, minute=30),
            content.start,
        )
        self.assertEqual(message, content.message)

    def test_date_error(self):
        with self.assertRaises(CommandError) as cm:
            self.call_command('invalid_date')

        self.assertEqual('The date is invalid', str(cm.exception))
