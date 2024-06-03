from datetime import timedelta
from functools import partial

from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme.creme_core.bricks import NotificationsBrick
from creme.creme_core.constants import UUID_CHANNEL_SYSTEM
from creme.creme_core.core.notification import (
    OUTPUT_EMAIL,
    OUTPUT_WEB,
    SimpleNotifContent,
)
from creme.creme_core.models import Notification, NotificationChannel
from creme.creme_core.notification import UpgradeAnnouncement
from creme.creme_core.utils.dates import dt_to_ISO8601
from creme.creme_core.views.notification import LastWebNotifications

from ..base import CremeTestCase
from .base import BrickTestCaseMixin


class NotificationViewsTestCase(BrickTestCaseMixin, CremeTestCase):
    LIST_URL = reverse('creme_core__notifications')
    LAST_URL = reverse('creme_core__last_web_notifications')
    DISCARD_URL = reverse('creme_core__discard_notification')
    ANNOUNCE_URL = reverse('creme_core__announce_upgrade')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        assert LastWebNotifications.limit == 10
        LastWebNotifications.limit = 2

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        LastWebNotifications.limit = 10

    def test_notifications01(self):
        user = self.login_as_standard()
        root = self.get_root_user()

        chan = NotificationChannel.objects.first()

        subject1 = 'Hello...'
        body1 = '...world'
        subject2 = 'Hi!'
        body2 = 'How are you?'
        create_notif = partial(
            Notification.objects.create, channel=chan, user=user, output=OUTPUT_WEB,
        )
        notif1 = create_notif(content=SimpleNotifContent(subject=subject1, body=body1))
        notif2 = create_notif(
            content=SimpleNotifContent(subject=subject2, body=body2),
            level=Notification.Level.HIGH,
        )
        create_notif(
            content=SimpleNotifContent(subject='Discarded', body='Ignored'),
            discarded=now() - timedelta(hours=1),
        )
        create_notif(
            content=SimpleNotifContent(subject='Other user', body='Ignored'),
            user=root,
        )
        create_notif(
            content=SimpleNotifContent(subject='No email', body='Ignored'),
            output=OUTPUT_EMAIL,
        )

        response1 = self.assertGET200(self.LIST_URL)
        brick_node = self.get_brick_node(
            self.get_html_tree(response1.content), brick=NotificationsBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=2,
            title='{count} Notification',
            plural_title='{count} Notifications',
        )
        # TODO: self.assertBrickHasAction(brick_node, url, action_type='edit')

        # ---
        response2 = self.assertGET200(self.LAST_URL)
        self.assertDictEqual(
            {
                'count': 2,
                'notifications': [
                    {
                        'id': notif2.id,
                        'channel': str(chan),
                        'level': 3,
                        'created': dt_to_ISO8601(notif2.created),
                        'subject': subject2,
                        'body': body2,
                    }, {
                        'id': notif1.id,
                        'channel': str(chan),
                        'level': 2,
                        'created': dt_to_ISO8601(notif1.created),
                        'subject': subject1,
                        'body': body1,
                    },
                ]
            },
            response2.json(),
        )

    def test_notifications02(self):
        "More than the limit."
        user = self.login_as_root_and_get()

        create_notif = partial(
            Notification.objects.create,
            channel=NotificationChannel.objects.first(),
            user=user, output=OUTPUT_WEB,
        )
        notifs = [
            create_notif(content=SimpleNotifContent(subject='Subject1', body='Body1')),
            create_notif(content=SimpleNotifContent(subject='Subject2', body='Body2')),
            create_notif(content=SimpleNotifContent(subject='Subject3', body='Body3')),
        ]

        content = self.assertGET200(self.LAST_URL).json()
        self.assertEqual(len(notifs), content['count'])
        self.assertListEqual(
            [notifs[2].id, notifs[1].id],
            [d['id'] for d in content['notifications']],
        )

    def test_discard_notification(self):
        user = self.login_as_standard()
        chan = NotificationChannel.objects.first()
        notif = Notification.objects.create(
            channel=chan, user=user,
            content=SimpleNotifContent(subject='Discarded soon', body='*Body*'),
        )
        old_created = notif.created - timedelta(hours=1)
        Notification.objects.filter(id=notif.id).update(created=old_created)

        url = self.DISCARD_URL
        data = {'id': notif.id}
        self.assertGET405(url, data=data)

        self.assertPOST200(url, data=data, follow=True)
        notif = self.assertStillExists(notif)
        self.assertDatetimesAlmostEqual(now(), notif.discarded)
        self.assertEqual(old_created, notif.created)  # No modified

    def test_discard_notification_error01(self):
        "Already discarded."
        user = self.login_as_standard()
        notif = Notification.objects.create(
            channel=NotificationChannel.objects.first(),
            user=user,
            content=SimpleNotifContent(subject='Discarded', body='*Body*'),
            discarded=now() - timedelta(hours=1),
        )
        # TODO: 409 instead? just ignore?
        self.assertPOST404(self.DISCARD_URL, data={'id': notif.id}, follow=True)

    def test_discard_notification_error02(self):
        "Belongs to another user."
        self.login_as_root()
        notif = Notification.objects.create(
            channel=NotificationChannel.objects.first(),
            user=self.create_user(),
            content=SimpleNotifContent(subject='Other user', body='*Body*'),
        )
        self.assertPOST404(self.DISCARD_URL, data={'id': notif.id}, follow=True)

    def test_announce_system_upgrade(self):
        user = self.login_as_super(is_staff=True)
        root = self.get_root_user()
        other = self.create_user(index=1, role=self.create_role())
        disabled = self.create_user(index=2, is_active=False)

        # ---
        list_response = self.assertGET200(self.LIST_URL)
        buttons_node = self.get_html_node_or_fail(
            self.get_html_tree(list_response.content),
            './/div[@class="buttons-list"]',
        )
        self.get_html_node_or_fail(
            buttons_node,
            f'.//a[@href="{self.ANNOUNCE_URL}"]',
        )

        # GET ---
        context1 = self.assertGET200(self.ANNOUNCE_URL).context
        self.assertEqual(_('Announce a system upgrade to users'), context1.get('title'))
        self.assertEqual(Notification.save_label,                 context1.get('submit_label'))

        with self.assertNoException():
            fields = context1['form'].fields

        self.assertIn('start',   fields)
        self.assertIn('message', fields)
        self.assertEqual(2, len(fields))

        # POST (error) ---
        now_value = now()
        yesterday = now_value - timedelta(days=1)
        response2 = self.assertPOST200(
            self.ANNOUNCE_URL, data={'start': self.formfield_value_date(yesterday)},
        )
        self.assertFormError(
            form=response2.context['form'],
            field='start',
            errors=_('Start must be in the future'),
        )

        # POST ---
        tomorrow = now_value + timedelta(days=1)
        tomorrow_evening = self.create_datetime(
            year=tomorrow.year,
            month=tomorrow.month,
            day=tomorrow.day,
            hour=23,
        )
        msg = 'The upgrade will probably take 2 hours.'
        response3 = self.client.post(
            self.ANNOUNCE_URL,
            follow=True,
            data={
                'start': self.formfield_value_datetime(tomorrow_evening),
                'message': msg,
            },
        )
        self.assertNoFormError(response3)

        notifications = {
            notif.user_id: notif
            for notif in Notification.objects.filter(channel__uuid=UUID_CHANNEL_SYSTEM)
        }
        root_notif = notifications.get(root.id)
        self.assertIsNotNone(root_notif)
        content = root_notif.content
        self.assertIsInstance(content, UpgradeAnnouncement)
        self.assertEqual(tomorrow_evening, content.start)
        self.assertEqual(msg,              content.message)

        other_notif = notifications.get(other.id)
        self.assertIsNotNone(other_notif)
        self.assertEqual(UpgradeAnnouncement.id, other_notif.content_id)

        self.assertNotIn(user.id,     notifications)
        self.assertNotIn(disabled.id, notifications)

        self.assertRedirects(response3, self.LIST_URL)

    def test_announce_system_upgrade_error(self):
        "Not staff user."
        self.login_as_super()
        self.assertGET403(self.ANNOUNCE_URL)
