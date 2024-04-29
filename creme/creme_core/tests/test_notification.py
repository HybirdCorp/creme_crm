from django.templatetags.tz import localtime
from django.utils.formats import date_format
from django.utils.html import escape
from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from creme.creme_core.core.notification import (
    OUTPUT_WEB,
    NotificationContent,
    notification_registry,
)
from creme.creme_core.models import FakeDocument, FakeFolder
from creme.creme_core.notification import (
    AdministrationChannelType,
    JobsChannelType,
    MassImportDoneContent,
    RemindersChannelType,
    SystemChannelType,
    UpgradeAnnouncement,
)
from creme.creme_core.tests.base import CremeTestCase


class NotificationTestCase(CremeTestCase):
    def test_system_channel(self):
        stype = SystemChannelType()
        self.assertEqual('creme_core-system', stype.id)
        self.assertEqual(
            pgettext('creme_core-channels', 'System'), str(stype.verbose_name),
        )
        self.assertEqual(_('System upgrades…'), stype.description)

        self.assertIsInstance(
            notification_registry.get_channel_type(stype.id),
            SystemChannelType,
        )

    def test_administration_channel(self):
        stype = AdministrationChannelType()
        self.assertEqual('creme_core-administration', stype.id)
        self.assertEqual(
            pgettext('creme_core-channels', 'Administration'),
            str(stype.verbose_name),
        )
        self.assertEqual(
            _('Important changes on your user like password change.'),
            stype.description,
        )

        self.assertIsInstance(
            notification_registry.get_channel_type(stype.id),
            AdministrationChannelType,
        )

    def test_jobs_channel(self):
        stype = JobsChannelType()
        self.assertEqual('creme_core-jobs', stype.id)
        self.assertEqual(_('Jobs'), stype.verbose_name)
        self.assertEqual(
            _('End of some long jobs (like CSV import).'),
            stype.description,
        )

        self.assertIsInstance(
            notification_registry.get_channel_type(stype.id),
            JobsChannelType,
        )

    def test_reminders_channel(self):
        stype = RemindersChannelType()
        self.assertEqual('creme_core-reminders', stype.id)
        self.assertEqual(_('Reminders'), stype.verbose_name)
        self.assertEqual(
            _(
                'The reminder feature is used by Alerts & ToDos '
                '(from the app Assistants) for example.'
            ),
            stype.description,
        )

        self.assertIsInstance(
            notification_registry.get_channel_type(stype.id),
            RemindersChannelType,
        )

    def test_upgrade_announcement01(self):
        "No extra message."
        user = self.get_root_user()
        dt = self.create_datetime(year=2023, month=11, day=12, hour=23, utc=True)
        announce1 = UpgradeAnnouncement(start=dt)
        self.assertEqual('creme_core-upgrade', announce1.id)
        data = announce1.as_dict()
        self.assertDictEqual({'start': '2023-11-12T23:00:00.000000Z'}, data)

        announce2 = UpgradeAnnouncement.from_dict(data)
        self.assertIsInstance(announce2, UpgradeAnnouncement)
        self.assertEqual(dt, announce2.start)

        self.assertEqual(
            _('An upgrade is planned'), announce2.get_subject(user),
        )
        self.assertEqual(
            _('An upgrade will be performed on %(start)s') % {
                'start': date_format(localtime(dt), 'DATETIME_FORMAT'),
            },
            announce2.get_body(user)
        )
        self.assertHTMLEqual(
            _('An upgrade will be performed on <strong>%(start)s</strong>') % {
                'start': date_format(localtime(dt), 'DATETIME_FORMAT'),
            },
            announce2.get_html_body(user)
        )

        self.assertIs(
            UpgradeAnnouncement,
            notification_registry.get_content_class(
                content_id=UpgradeAnnouncement.id,
                output=OUTPUT_WEB,
            ),
        )

        # Deserialization errors
        with self.assertRaises(NotificationContent.DeserializationError):
            UpgradeAnnouncement.from_dict({})

        with self.assertRaises(NotificationContent.DeserializationError):
            UpgradeAnnouncement.from_dict({'start': 1})

        with self.assertRaises(NotificationContent.DeserializationError):
            UpgradeAnnouncement.from_dict({'start': 'not a date'})

    def test_upgrade_announcement02(self):
        "Extra message."
        user = self.get_root_user()
        dt = self.create_datetime(year=2023, month=12, day=3, hour=8, utc=True)
        msg = "Don't be afraid."
        announce1 = UpgradeAnnouncement(start=dt, message=msg)
        data = announce1.as_dict()
        self.assertDictEqual(
            {
                'start': '2023-12-03T08:00:00.000000Z',
                'message': msg,
            },
            data,
        )

        announce2 = UpgradeAnnouncement.from_dict(data)
        self.assertEqual(dt, announce2.start)
        self.assertEqual(msg, announce2.message)

        self.assertEqual(
            _('An upgrade will be performed on %(start)s.\n%(message)s') % {
                'start': date_format(localtime(dt), 'DATETIME_FORMAT'),
                'message': msg,
            },
            announce2.get_body(user)
        )
        self.assertHTMLEqual(
            _('An upgrade will be performed on <strong>%(start)s</strong>.<br>%(message)s') % {
                'start': date_format(localtime(dt), 'DATETIME_FORMAT'),
                'message': escape(msg),
            },
            announce2.get_html_body(user)
        )

        # Deserialization errors
        with self.assertRaises(NotificationContent.DeserializationError):
            UpgradeAnnouncement.from_dict({
                'start': '2023-12-03T08:00:00.000000Z',
                'message': 10,  # Not a string
            })

    def test_mass_import_done(self):
        user = self.get_root_user()
        folder = FakeFolder.objects.create(user=user, title='CSV docs')
        doc = FakeDocument.objects.create(
            user=user,
            title='CSV with contacts #1',
            linked_folder=folder,
            # filedata=...,
        )
        content = MassImportDoneContent(instance=doc)
        self.assertEqual(_('A mass import is done'), content.get_subject(user))
        self.assertEqual(
            _('The mass import for document «%(object)s» is done') % {'object': doc},
            content.get_body(user),
        )
        self.assertEqual(
            _('The mass import for %(document)s is done') % {
                'document': f'<a href="{doc.get_absolute_url()}" target="_self">{doc}</a>',
            },
            content.get_html_body(user),
        )

    def test_mass_import_done_error(self):
        user = self.get_root_user()
        pk = self.UNUSED_PK
        content = MassImportDoneContent(instance=pk)
        self.assertEqual(_('A mass import is done'), content.get_subject(user))

        body = _('The document is deleted')
        self.assertEqual(body, content.get_body(user))
        self.assertEqual(body, content.get_html_body(user))
