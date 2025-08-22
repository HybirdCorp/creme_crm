from functools import partial
from uuid import UUID, uuid4

from django.utils.timezone import now
from django.utils.translation import pgettext

from creme.creme_core import constants
# Should be a test queue
from creme.creme_core.core.job import get_queue
from creme.creme_core.core.notification import (
    OUTPUT_EMAIL,
    OUTPUT_WEB,
    SimpleNotifContent,
)
from creme.creme_core.creme_jobs import (
    notification_emails_sender_type as sender_type,
)
from creme.creme_core.models import (
    Job,
    Notification,
    NotificationChannel,
    NotificationChannelConfigItem,
)
from creme.creme_core.notification import (
    AdministrationChannelType,
    JobsChannelType,
    RemindersChannelType,
    SystemChannelType,
    UpgradeAnnouncement,
)
from creme.creme_core.utils.dates import dt_to_ISO8601

from ..base import CremeTestCase


class NotificationChannelTestCase(CremeTestCase):
    def test_manager_create__custom(self):
        "Custom."
        name = 'My_channel'
        description = 'Very useful'
        channel = NotificationChannel.objects.create(
            name=name, description=description, default_outputs=[OUTPUT_WEB],
        )
        self.assertIsInstance(channel.uuid, UUID)
        self.assertEqual(name, channel.name)
        self.assertEqual(name, channel.final_name)
        self.assertEqual(name, str(channel))
        self.assertEqual(description, channel.description)
        self.assertEqual(description, channel.final_description)
        self.assertEqual('', channel.type_id)
        self.assertIs(channel.required, True)
        self.assertIsNone(channel.deleted)

        default_outputs = channel.default_outputs
        self.assertListEqual([OUTPUT_WEB], default_outputs)

        self.assertIsNone(channel.type)

        self.assertEqual(name, str(channel))

    def test_manager_create__not_custom(self):
        "Not custom + not required."
        uid = uuid4()
        channel = NotificationChannel.objects.create(
            uuid=uid, type_id=SystemChannelType.id, required=False,
            default_outputs=[OUTPUT_EMAIL],
        )
        self.assertEqual(uid, channel.uuid)
        self.assertEqual(SystemChannelType.id, channel.type_id)
        self.assertFalse(channel.required)
        self.assertEqual('', channel.name)
        self.assertEqual(SystemChannelType.verbose_name, channel.final_name)
        self.assertEqual(SystemChannelType.verbose_name, str(channel))
        self.assertEqual('', channel.description)
        self.assertEqual(SystemChannelType.description, channel.final_description)
        self.assertListEqual([OUTPUT_EMAIL], channel.default_outputs)

        self.assertIsInstance(channel.type, SystemChannelType)

        self.assertEqual(SystemChannelType.verbose_name, str(channel))

    def test_manager_create_error(self):
        "No Output."
        with self.assertRaises(ValueError) as cm:
            NotificationChannel.objects.create(
                name='My_channel', description='Very useful',
            )

        self.assertEqual(
            'The field "default_outputs" cannot be empty.', str(cm.exception),
        )

    def test_manager_get_for_uuid(self):
        uid1 = uuid4()
        chan = NotificationChannel.objects.create(
            uuid=uid1, name='My channel', default_outputs=[OUTPUT_WEB],
        )

        self.assertEqual(chan, NotificationChannel.objects.get_for_uuid(uid1))

        with self.assertNumQueries(0):
            self.assertEqual(chan, NotificationChannel.objects.get_for_uuid(str(uid1)))

        self.assertNotEqual(
            chan, NotificationChannel.objects.get_for_uuid(constants.UUID_CHANNEL_SYSTEM)
        )

        # ---
        uid2 = uuid4()
        with self.assertLogs(level='CRITICAL') as logs_manager:
            with self.assertRaises(NotificationChannel.DoesNotExist):
                NotificationChannel.objects.get_for_uuid(uid2)
        self.assertListEqual(
            logs_manager.output,
            [
                f'CRITICAL:'
                f'creme.creme_core.models.notification:'
                f'the Channel with uuid="{uid2}" does not exist; '
                f'have you run the command "creme_populate"?!'
            ],
        )

    def test_property_type(self):
        uid = uuid4()
        channel = NotificationChannel.objects.create(
            uuid=uid, type=SystemChannelType, required=False,
            default_outputs=[OUTPUT_EMAIL],
        )
        self.assertEqual(SystemChannelType.id, channel.type_id)

        chan_type = channel.type
        self.assertIsInstance(chan_type, SystemChannelType)
        self.assertIs(chan_type, channel.type)

        # ---
        channel.type = JobsChannelType
        self.assertIsInstance(channel.type, JobsChannelType)

        # ---
        channel.type = None
        self.assertIsNone(channel.type)


class NotificationChannelConfigItemTestCase(CremeTestCase):
    def test_manager_create01(self):
        "No output."
        channel = self.get_object_or_fail(NotificationChannel, uuid=constants.UUID_CHANNEL_SYSTEM)
        user = self.create_user()
        ncci = NotificationChannelConfigItem.objects.create(channel=channel, user=user)
        self.assertEqual(channel, ncci.channel)
        self.assertEqual(user,    ncci.user)
        self.assertListEqual([], ncci.outputs)

    def test_manager_create02(self):
        "One output."
        channel = self.get_object_or_fail(NotificationChannel, uuid=constants.UUID_CHANNEL_SYSTEM)
        user = self.create_user()
        ncci = NotificationChannelConfigItem.objects.create(
            channel=channel, user=user, outputs=[OUTPUT_WEB],
        )
        outputs = ncci.outputs
        self.assertListEqual(['web'], outputs)
        self.assertListEqual([OUTPUT_WEB], outputs)

    def test_manager_smart_create(self):
        channel = NotificationChannel.objects.create(default_outputs=[OUTPUT_WEB])
        user = self.create_user()
        ncci = NotificationChannelConfigItem.objects.smart_create(
            channel=channel, user=user,
        )
        self.assertIsInstance(ncci, NotificationChannelConfigItem)
        self.assertIsNotNone(ncci.pk)
        self.assertEqual(channel, ncci.channel)
        self.assertEqual(user,    ncci.user)
        self.assertListEqual([OUTPUT_WEB], ncci.outputs)

    def test_manager_bulk_get(self):
        create_chan = NotificationChannel.objects.create
        chan1 = create_chan(name='Chan #1', default_outputs=[OUTPUT_WEB])
        chan2 = create_chan(name='Chan #2', default_outputs=[OUTPUT_EMAIL])

        user1 = self.get_root_user()
        user2 = self.create_user()
        item1 = NotificationChannelConfigItem.objects.create(
            channel=chan1, user=user1, outputs=[OUTPUT_EMAIL],
        )

        # 1*SELECT + 3*(SAVEPOINT+CREATE+RELEASE)
        with self.assertNumQueries(10):
            items = [
                *NotificationChannelConfigItem.objects.bulk_get(
                    channels=[chan1, chan2], users=[user1, user2],
                ),
            ]

        self.assertIsList(items, length=4)

        self.assertListEqual(
            [NotificationChannelConfigItem] * 4,
            [type(item) for item in items],
        )
        # self.assertAll(item.pk for item in items) TODO?
        self.assertTrue(all(item.pk for item in items))

        def find_item(user, channel):
            for item in items:
                if item.channel == channel and item.user == user:
                    return item

            self.fail(f'Item not found for channel={channel} & user={user}')

        item11 = find_item(user=user1, channel=chan1)
        self.assertEqual(item1, item11)
        self.assertListEqual([OUTPUT_EMAIL], item11.outputs)

        item12 = find_item(user=user1, channel=chan2)
        self.assertListEqual([OUTPUT_EMAIL], item12.outputs)

        item21 = find_item(user=user2, channel=chan1)
        self.assertListEqual([OUTPUT_WEB], item21.outputs)

        item22 = find_item(user=user2, channel=chan2)
        self.assertListEqual([OUTPUT_EMAIL], item22.outputs)

        # Cache
        with self.assertNumQueries(0):
            items_again = [
                *NotificationChannelConfigItem.objects.bulk_get(
                    channels=[chan2, chan1], users=[user2, user1],
                ),
            ]

        self.assertCountEqual(
            [item.id for item in items], [item.id for item in items_again],
        )

    def test_manager_bulk_get__complete_cache(self):
        user = self.get_root_user()

        create_chan = NotificationChannel.objects.create
        chan1 = create_chan(name='Chan #1', default_outputs=[OUTPUT_WEB])
        self.get_alone_element(NotificationChannelConfigItem.objects.bulk_get(
            channels=[chan1], users=[user],
        ))

        chan2 = create_chan(name='Chan #2', default_outputs=[OUTPUT_EMAIL])
        item2 = NotificationChannelConfigItem.objects.smart_create(channel=chan2, user=user)
        with self.assertNumQueries(1):
            retrieved_item2 = self.get_alone_element(
                NotificationChannelConfigItem.objects.bulk_get(channels=[chan2], users=[user])
            )
        self.assertIsInstance(retrieved_item2, NotificationChannelConfigItem)
        self.assertEqual(item2.pk, retrieved_item2.pk)

        # ---
        with self.assertNumQueries(0):
            self.get_alone_element(
                NotificationChannelConfigItem.objects.bulk_get(channels=[chan2], users=[user])
            )

    def test_manager_bulk_get__complete_cache_with_creation(self):
        user = self.get_root_user()

        create_chan = NotificationChannel.objects.create
        chan1 = create_chan(name='Chan #1', default_outputs=[OUTPUT_WEB])
        self.get_alone_element(NotificationChannelConfigItem.objects.bulk_get(
            channels=[chan1], users=[user],
        ))

        chan2 = create_chan(name='Chan #2', default_outputs=[OUTPUT_EMAIL])
        item2 = self.get_alone_element(NotificationChannelConfigItem.objects.bulk_get(
            channels=[chan2], users=[user],
        ))
        self.assertIsNotNone(item2.pk)
        self.assertEqual(user, item2.user)
        self.assertEqual(chan2, item2.channel)
        self.assertListEqual([OUTPUT_EMAIL], item2.outputs)

        # ---
        with self.assertNumQueries(0):
            self.get_alone_element(NotificationChannelConfigItem.objects.bulk_get(
                channels=[chan2], users=[user],
            ))


class NotificationTestCase(CremeTestCase):
    def get_emails_sender_job(self):
        return self.get_object_or_fail(Job, type_id=sender_type.id)

    def test_content01(self):
        "With SimpleNotifContent."
        subject = 'Aleeeeert!!!'
        body = 'You are late'
        snc = SimpleNotifContent(subject=subject, body=body)

        notif = Notification()

        with self.assertRaises(ValueError):
            notif.content  # NOQA

        notif.content = snc
        self.assertEqual(snc.id, notif.content_id)
        self.assertDictEqual(snc.as_dict(), notif.content_data)
        self.assertEqual(snc, notif.content)

    def test_content02(self):
        "With UpgradeAnnouncement."
        dt = self.create_datetime(year=2023, month=12, day=24, hour=13)
        announce = UpgradeAnnouncement(start=dt)

        notif = Notification()
        notif.content = announce
        self.assertEqual(announce.id, notif.content_id)
        self.assertDictEqual(announce.as_dict(), notif.content_data)
        self.assertEqual(announce, notif.content)

    def test_manager_create(self):
        user = self.get_root_user()
        chan = NotificationChannel.objects.first()
        snc = SimpleNotifContent(subject='Hello...', body='..world')

        notif = Notification.objects.create(channel=chan, user=user, content=snc)
        notif = self.refresh(notif)
        self.assertEqual(chan, notif.channel)
        self.assertEqual(user, notif.user)
        self.assertEqual(Notification.Level.NORMAL, notif.level)
        self.assertDatetimesAlmostEqual(notif.created, now())
        self.assertIs(notif.discarded, None)
        self.assertEqual(snc, notif.content)

    def test_to_dict01(self):
        user = self.get_root_user()
        chan = self.get_object_or_fail(NotificationChannel, uuid=constants.UUID_CHANNEL_SYSTEM)
        subject = 'Hello...'
        body = '..world'
        snc = SimpleNotifContent(subject=subject, body=body)

        notif = Notification.objects.create(channel=chan, user=user, content=snc)
        self.assertDictEqual(
            {
                'id': notif.id,
                'channel': pgettext('creme_core-channels', 'System'),
                'created': dt_to_ISO8601(notif.created),
                'level': Notification.Level.NORMAL,
                'subject': subject,
                'body': body,
            },
            notif.to_dict(user),
        )

    def test_to_dict02(self):
        user = self.get_root_user()
        chan = self.get_object_or_fail(NotificationChannel, uuid=constants.UUID_CHANNEL_ADMIN)

        subject = 'Very important'
        html_body = 'I <b>should</b> be used'
        snc = SimpleNotifContent(
            subject=subject, body='Should not be used', html_body=html_body,
        )

        notif = Notification.objects.create(
            channel=chan, user=user, content=snc, level=Notification.Level.HIGH,
        )
        self.assertDictEqual(
            {
                'id': notif.id,
                'channel': pgettext('creme_core-channels', 'Administration'),
                'created': dt_to_ISO8601(notif.created),
                'level': Notification.Level.HIGH,
                'subject': subject,
                'body': html_body,
            },
            notif.to_dict(user),
        )

    def test_manager_send01(self):
        "One user, Channel UUID (string), default priority."
        queue = get_queue()
        queue.clear()

        user = self.get_root_user()
        uid = constants.UUID_CHANNEL_ADMIN
        channel = self.get_object_or_fail(NotificationChannel, uuid=uid)
        NotificationChannelConfigItem.objects.create(
            channel=channel, user=user, outputs=[OUTPUT_WEB],
        )

        old_count = Notification.objects.count()
        subject = 'Hi'
        body = 'there'
        notifications = Notification.objects.send(
            users=[user],
            channel=constants.UUID_CHANNEL_ADMIN,
            content=SimpleNotifContent(subject=subject, body=body),
        )
        self.assertIsList(notifications, length=1)

        self.assertEqual(old_count + 1, Notification.objects.count())
        notif = self.get_object_or_fail(
            Notification,
            user=user, channel__uuid=constants.UUID_CHANNEL_ADMIN,
        )
        self.assertEqual(SimpleNotifContent.id, notif.content_id)
        exp_data = {'subject': subject, 'body': body}
        self.assertDictEqual(exp_data, notif.content_data)
        self.assertIsNone(notif.discarded)
        self.assertEqual(Notification.Level.NORMAL, notif.level)
        self.assertEqual(OUTPUT_WEB,                notif.output)
        self.assertDictEqual({}, notif.extra_data)

        self.assertFalse(queue.refreshed_jobs)

        notif0 = notifications[0]
        self.assertIsInstance(notif0, Notification)
        # self.assertEqual(notif.pk, notif0.pk)  # depends on data-base engine
        self.assertEqual(SimpleNotifContent.id, notif0.content_id)
        self.assertDictEqual(exp_data,          notif0.content_data)

    def test_manager_send02(self):
        "Two users, Channel instance, low priority, other outputs."
        queue = get_queue()
        queue.clear()

        user1 = self.get_root_user()
        user2 = self.create_user()
        old_count = Notification.objects.count()
        channel = NotificationChannel.objects.create(
            name='My Channel', default_outputs=[OUTPUT_WEB],
        )

        create_item = partial(NotificationChannelConfigItem.objects.create, channel=channel)
        create_item(user=user1, outputs=[OUTPUT_WEB])
        create_item(user=user2, outputs=[OUTPUT_EMAIL])

        level = Notification.Level.LOW
        notifications = Notification.objects.send(
            users=[user1, user2],
            channel=channel,
            content=SimpleNotifContent(subject='*Subject*', body='*Body*'),
            level=level,
        )
        self.assertIsList(notifications, length=2)
        self.assertEqual(old_count + 2, Notification.objects.count())

        notif1 = self.get_object_or_fail(Notification, user=user1, channel=channel)
        self.assertEqual(level, notif1.level)
        self.assertEqual(OUTPUT_WEB, notif1.output)

        notif2 = self.get_object_or_fail(Notification, user=user2, channel=channel)
        self.assertEqual(OUTPUT_EMAIL, notif2.output)

        job, _data = self.get_alone_element(queue.refreshed_jobs)
        self.assertEqual(self.get_emails_sender_job(), job)

    def test_manager_send03(self):
        "UUID instance + teams (avoid duplicates) + create config lazily."
        user1 = self.get_root_user()
        user2 = self.create_user(0)
        user3 = self.create_user(1)

        team = self.create_team('Guild', user1, user3)

        old_count = Notification.objects.count()
        channel = NotificationChannel.objects.create(
            name='My Channel', default_outputs=[OUTPUT_WEB],
        )
        Notification.objects.send(
            users=[user1, team, user2],
            channel=channel.uuid,
            content=SimpleNotifContent(subject='*Subject*', body='*Body*'),
        )
        self.assertEqual(old_count + 3, Notification.objects.count())
        self.get_object_or_fail(Notification, user=user1, channel=channel)
        self.get_object_or_fail(Notification, user=user2, channel=channel)
        self.get_object_or_fail(Notification, user=user3, channel=channel)

    def test_manager_send04(self):
        "No output."
        user = self.get_root_user()
        channel = NotificationChannel.objects.create(
            name='My Channel', default_outputs=[OUTPUT_WEB],
        )
        NotificationChannelConfigItem.objects.create(
            channel=channel, user=user, outputs=[],
        )

        old_count = Notification.objects.count()
        Notification.objects.send(
            users=[user],
            channel=channel,
            content=SimpleNotifContent(subject='*Subject*', body='*Body*'),
        )
        self.assertEqual(old_count, Notification.objects.count())

    def test_manager_send05(self):
        "Several outputs."
        user = self.get_root_user()
        channel = NotificationChannel.objects.create(
            name='My Channel', default_outputs=[OUTPUT_WEB],
        )
        NotificationChannelConfigItem.objects.create(
            channel=channel, user=user, outputs=[OUTPUT_WEB, OUTPUT_EMAIL],
        )

        old_count = Notification.objects.count()
        Notification.objects.send(
            users=[user], channel=channel,
            content=SimpleNotifContent(subject='*Subject*', body='*Body*'),
        )
        self.assertEqual(old_count + 2, Notification.objects.count())

        self.get_object_or_fail(
            Notification, user=user, channel=channel, output=OUTPUT_WEB,
        )
        self.get_object_or_fail(
            Notification, user=user, channel=channel, output=OUTPUT_EMAIL,
        )

    def test_manager_send__extra_data(self):
        user = self.get_root_user()
        channel = NotificationChannel.objects.create(
            name='My Channel', default_outputs=[OUTPUT_WEB],
        )

        old_count = Notification.objects.count()
        extra_data = {'foo': 'bar'}
        Notification.objects.send(
            users=[user],
            channel=channel,
            content=SimpleNotifContent(subject='*Subject*', body='*Body*'),
            extra_data=extra_data,
        )
        self.assertEqual(old_count + 1, Notification.objects.count())

        notif = self.get_object_or_fail(
            Notification, user=user, channel=channel, output=OUTPUT_WEB,
        )
        self.assertDictEqual(extra_data, notif.extra_data)

    def test_populate(self):
        sys_chan = self.get_object_or_fail(
            NotificationChannel, uuid=constants.UUID_CHANNEL_SYSTEM,
        )
        self.assertEqual('', sys_chan.name)
        self.assertEqual('', sys_chan.description)
        self.assertEqual(SystemChannelType.id, sys_chan.type_id)
        self.assertIsInstance(sys_chan.type, SystemChannelType)
        self.assertTrue(sys_chan.required)
        self.assertIsNone(sys_chan.deleted)

        # ---
        admin_chan = self.get_object_or_fail(
            NotificationChannel, uuid=constants.UUID_CHANNEL_ADMIN,
        )
        self.assertEqual('', admin_chan.name)
        self.assertEqual('', admin_chan.description)
        self.assertIsInstance(admin_chan.type, AdministrationChannelType)
        self.assertFalse(admin_chan.required)
        self.assertIsNone(admin_chan.deleted)

        # ---
        jobs_chan = self.get_object_or_fail(
            NotificationChannel, uuid=constants.UUID_CHANNEL_JOBS,
        )
        self.assertEqual('', jobs_chan.name)
        self.assertEqual('', jobs_chan.description)
        self.assertIsInstance(jobs_chan.type, JobsChannelType)
        self.assertFalse(jobs_chan.required)

        # ---
        rem_chan = self.get_object_or_fail(
            NotificationChannel, uuid=constants.UUID_CHANNEL_REMINDERS,
        )
        self.assertEqual('', rem_chan.name)
        self.assertEqual('', rem_chan.description)
        self.assertIsInstance(rem_chan.type, RemindersChannelType)
        self.assertTrue(rem_chan.required)
