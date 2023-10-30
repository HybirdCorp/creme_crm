from functools import partial

from django.conf import settings
# from django.core import mail
from django.core.mail.backends.locmem import EmailBackend
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _

# Should be a test queue
from creme.creme_core.core.job import get_queue
from creme.creme_core.core.notification import (
    OUTPUT_EMAIL,
    OUTPUT_WEB,
    notification_registry,
)
# from creme.creme_core.models import Job, JobResult,
from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickHomeLocation,
    FakeOrganisation,
    Notification,
    NotificationChannel,
)
from creme.creme_core.tests.views.base import BrickTestCaseMixin

from ..bricks import UserMessagesBrick
from ..constants import UUID_CHANNEL_USERMESSAGES
# from ..creme_jobs import usermessages_send_type
from ..models import UserMessage, UserMessagePriority
from ..notification import MessageSentContent, UserMessagesChannelType
from .base import AssistantsTestCase


class UserMessageTestCase(BrickTestCaseMixin, AssistantsTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.original_send_messages = EmailBackend.send_messages

    def tearDown(self):
        super().tearDown()
        EmailBackend.send_messages = self.original_send_messages

    @staticmethod
    def _build_add_url(entity=None):
        return reverse(
            'assistants__create_related_message', args=(entity.id,),
        ) if entity else reverse(
            'assistants__create_message',
        )

    def _create_usermessage(self, title, body, priority, users, entity):
        if priority is None:
            priority = UserMessagePriority.objects.create(title='Important')

        response = self.client.post(
            self._build_add_url(entity),
            data={
                'user':     self.user.pk,
                'title':    title,
                'body':     body,
                'priority': priority.id,
                'users':    [u.id for u in users],
            },
        )
        self.assertNoFormError(response)

    # def _get_usermessages_job(self):
    #     return self.get_object_or_fail(Job, type_id=usermessages_send_type.id)

    def test_message_sent_content01(self):
        sender = self.get_root_user()
        recipient = self.create_user()
        msg = UserMessage.objects.create(
            sender=sender, recipient=recipient, creation_date=now(),
            title='An invoice have been created',
            body='Total: 1500$\nDeadline: 25/12/2025',
            priority=UserMessagePriority.objects.first(),
        )
        content1 = MessageSentContent(instance=msg)
        content2 = MessageSentContent.from_dict(content1.as_dict())
        self.assertEqual(
            _('You received a user message from «%(sender)s»') % {'sender': sender},
            content2.get_subject(user=recipient),
        )
        self.assertEqual(
            _('Title: %(message_title)s\nBody: %(message_body)s') % {
                'message_title': msg.title, 'message_body': msg.body,
            },
            content2.get_body(user=sender),
        )
        self.assertHTMLEqual(
            '<h1>{title}</h1><p>{body}</p>'.format(
                title=msg.title,
                body=msg.body.replace('\n', '<br>'),
            ),
            content2.get_html_body(user=sender),
        )

    def test_message_sent_content02(self):
        "Related entity."
        entity = self.entity
        sender = self.get_root_user()
        recipient = self.create_user()
        msg = UserMessage.objects.create(
            sender=sender, recipient=recipient, creation_date=now(),
            title='An invoice have been created',
            body='Total: 1500$<script>alert("pwned")</script>',
            priority=UserMessagePriority.objects.first(),
            real_entity=entity,
        )
        content1 = MessageSentContent(instance=msg)
        content2 = MessageSentContent.from_dict(content1.as_dict())
        self.assertEqual(
            _('You received a user message from «%(sender)s»') % {'sender': sender},
            content2.get_subject(user=recipient),
        )
        self.maxDiff = None
        self.assertEqual(
            '{}\n{}'.format(
                _('Title: %(message_title)s\nBody: %(message_body)s') % {
                    'message_title': msg.title, 'message_body': msg.body,
                },
                _('Related entity: %(message_entity)s') % {'message_entity': entity},
            ),
            content2.get_body(user=sender),
        )
        self.assertHTMLEqual(
            '<h1>An invoice have been created</h1>'
            '<p>Total: 1500$&lt;script&gt;alert(&quot;pwned&quot;)&lt;/script&gt;</p>'
            + _('Related to %(entity)s') % {
                'entity': f'<a href="{entity.get_absolute_url()}" target="_self">{entity}</a>'
            },
            content2.get_html_body(user=sender),
        )

    def test_message_sent_content_error(self):
        "UserMessage does not exist anymore."
        user = self.get_root_user()
        content = MessageSentContent.from_dict({'instance': self.UNUSED_PK})
        self.assertEqual(
            _('You received a user message'),
            content.get_subject(user=user),
        )
        body = _('The message has been deleted')
        self.assertEqual(body, content.get_body(user=user))
        self.assertEqual(body, content.get_html_body(user=user))

    def test_channel(self):
        chan_type = UserMessagesChannelType()
        self.assertEqual('assistants-user_messages', chan_type.id)
        self.assertEqual(_('User messages'), chan_type.verbose_name)
        self.assertEqual(
            _('A user message has been received (app: Assistants)'),
            chan_type.description,
        )

        self.assertIsInstance(
            notification_registry.get_channel_type(chan_type.id),
            UserMessagesChannelType,
        )

    def test_populate(self):
        self.assertEqual(3, UserMessagePriority.objects.count())

        chan = self.get_object_or_fail(NotificationChannel, uuid=UUID_CHANNEL_USERMESSAGES)
        self.assertTrue(chan.required)
        self.assertFalse(chan.name)
        self.assertEqual(UserMessagesChannelType.id, chan.type_id)

    def test_create01(self):
        self.assertFalse(UserMessage.objects.exists())

        queue = get_queue()
        queue.clear()

        entity = self.entity
        response = self.assertGET200(self._build_add_url(entity))
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/add-popup.html')

        context = response.context
        self.assertEqual(
            _('New message about «{entity}»').format(entity=entity),
            context.get('title'),
        )
        self.assertEqual(_('Save the message'), context.get('submit_label'))

        title = 'TITLE'
        body = 'BODY'
        priority = UserMessagePriority.objects.create(title='Important')
        user1 = self.create_user(
            username='User01', email='user01@foobar.com', first_name='User01', last_name='Foo',
        )
        self._create_usermessage(title, body, priority, [user1], entity)

        message = self.get_alone_element(UserMessage.objects.all())
        self.assertEqual(title,    message.title)
        self.assertEqual(body,     message.body)
        self.assertEqual(priority, message.priority)
        # self.assertFalse(message.email_sent)

        self.assertEqual(entity.id,             message.entity_id)
        self.assertEqual(entity.entity_type_id, message.entity_content_type_id)

        self.assertEqual(self.user, message.sender)
        self.assertEqual(user1,    message.recipient)

        self.assertDatetimesAlmostEqual(now(), message.creation_date)

        self.assertEqual(title, str(message))

        # job, _data = self.get_alone_element(queue.refreshed_jobs)
        # self.assertEqual(self._get_usermessages_job(), job)
        notif1 = self.get_object_or_fail(
            Notification,
            user=user1, channel__uuid=UUID_CHANNEL_USERMESSAGES, output=OUTPUT_WEB,
        )
        self.assertEqual(MessageSentContent.id, notif1.content_id)
        self.assertDictEqual({'instance': message.id}, notif1.content_data)

        self.get_object_or_fail(
            Notification,
            user=user1, channel__uuid=UUID_CHANNEL_USERMESSAGES, output=OUTPUT_EMAIL,
        )

    @override_settings(SOFTWARE_LABEL='My CRM')
    def test_create02(self):
        "2 users."
        # now_value = now()
        priority = UserMessagePriority.objects.create(title='Important')

        user1 = self.create_user(index=0)
        user2 = self.create_user(index=1)

        # job = self._get_usermessages_job()
        # self.assertIsNone(job.user)
        # self.assertIsNone(job.type.next_wakeup(job, now_value))

        title = 'TITLE'
        body  = 'BODY'
        self._create_usermessage(title, body, priority, [user1, user2], self.entity)

        messages = UserMessage.objects.all()
        self.assertCountEqual([user1, user2], [msg.recipient for msg in messages])

        # self.assertIs(now_value, job.type.next_wakeup(job, now_value))

        # usermessages_send_type.execute(job)

        # messages = mail.outbox
        # self.assertEqual(len(messages), 2)
        #
        # message = messages[0]
        # software = 'My CRM'
        # self.assertEqual(
        #     _('User message from {software}: {title}').format(software=software, title=title),
        #     message.subject,
        # )
        # self.assertEqual(
        #     _('{user} sent you the following message:\n{body}').format(
        #         user=self.user,
        #         body=body,
        #     ),
        #     message.body,
        # )
        # self.assertEqual(settings.EMAIL_SENDER, message.from_email)
        # self.assertHasNoAttr(message, 'alternatives')
        # self.assertFalse(message.attachments)
        #
        # for user_msg in UserMessage.objects.all():
        #     self.assertTrue(user_msg.email_sent)

    def test_create03(self):
        "Without related entity."
        response = self.assertGET200(self._build_add_url())
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/add-popup.html')

        context = response.context
        self.assertEqual(_('New message'),      context.get('title'))
        self.assertEqual(_('Save the message'), context.get('submit_label'))

        priority = UserMessagePriority.objects.create(title='Important')
        user1 = self.create_user(index=0)

        self._create_usermessage('TITLE', 'BODY', priority, [user1], None)

        message = self.get_alone_element(UserMessage.objects.all())
        self.assertIsNone(message.entity_id)
        self.assertIsNone(message.entity_content_type_id)
        self.assertIsNone(message.real_entity)

    def test_create04(self):
        "One team."
        users = [self.create_user(index=i) for i in range(2)]
        team = self.create_team('Team', *users)

        self._create_usermessage('TITLE', 'BODY', None, [team], self.entity)
        self.assertCountEqual(users, [msg.recipient for msg in UserMessage.objects.all()])

    def test_create05(self):
        "Teams and isolated users with non-void intersections."
        users = [self.create_user(index=i) for i in range(4)]

        team1 = self.create_team('Team01', *users[:2])
        team2 = self.create_team('Team02', *users[1:3])

        self._create_usermessage(
            'TITLE', 'BODY', None, [team1, team2, users[0], users[3]], self.entity,
        )
        self.assertCountEqual(
            users, [msg.recipient for msg in UserMessage.objects.all()],
        )

    def test_brick(self):
        user = self.user
        other_user = self.create_user()
        priority = UserMessagePriority.objects.first()

        entity1 = self.entity

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        entity2 = create_orga(name='Acme')
        del_entity = create_orga(name='Deleted', is_deleted=True)

        def create_message(entity, title):
            return UserMessage.objects.create(
                title=title,
                body='My body is ready',
                creation_date=now(),
                priority=priority,
                sender=other_user,
                recipient=user,
                real_entity=entity,
            )

        msg1 = create_message(entity1, 'Recall')
        msg2 = create_message(entity1, "It's important")
        msg3 = create_message(entity2, 'Other message')
        msg4 = create_message(del_entity, 'Should not be visible')
        msg5 = create_message(None, 'Only on home')

        UserMessagesBrick.page_size = max(4, settings.BLOCK_SIZE)

        def message_found(brick_node, msg):
            title = msg.title
            return any(n.text == title for n in brick_node.findall('.//td'))

        BrickDetailviewLocation.objects.create_if_needed(
            brick=UserMessagesBrick,
            model=type(entity1),
            order=50,
            zone=BrickDetailviewLocation.TOP,
        )

        response1 = self.assertGET200(self.entity.get_absolute_url())
        detail_brick_node = self.get_brick_node(
            self.get_html_tree(response1.content), brick=UserMessagesBrick,
        )

        self.assertTrue(message_found(detail_brick_node, msg1))
        self.assertTrue(message_found(detail_brick_node, msg2))
        self.assertFalse(message_found(detail_brick_node, msg3))
        self.assertFalse(message_found(detail_brick_node, msg4))
        self.assertFalse(message_found(detail_brick_node, msg5))

        # ---
        BrickHomeLocation.objects.get_or_create(
            brick_id=UserMessagesBrick.id, defaults={'order': 50},
        )

        response2 = self.assertGET200(reverse('creme_core__home'))
        home_brick_node = self.get_brick_node(
            self.get_html_tree(response2.content), brick=UserMessagesBrick,
        )

        self.assertTrue(message_found(home_brick_node, msg1))
        self.assertTrue(message_found(home_brick_node, msg2))
        self.assertTrue(message_found(home_brick_node, msg3))
        self.assertInstanceLink(home_brick_node, entity1)
        self.assertInstanceLink(home_brick_node, entity2)
        self.assertFalse(message_found(home_brick_node, msg4))
        self.assertTrue(message_found(home_brick_node, msg5))

    def test_delete_related01(self):
        priority = UserMessagePriority.objects.create(title='Important')
        self._create_usermessage('TITLE', 'BODY', priority, [self.user], self.entity)

        self.assertEqual(1, UserMessage.objects.count())

        self.entity.delete()
        self.assertFalse(UserMessage.objects.all())

    def test_delete(self):
        user = self.user
        other_user = self.create_user()

        priority = UserMessagePriority.objects.create(title='Important')
        self._create_usermessage(
            'TITLE', 'BODY', priority, users=[user, other_user], entity=None,
        )

        messages = {msg.recipient_id: msg for msg in UserMessage.objects.all()}
        self.assertEqual(2, len(messages))

        url = reverse('assistants__delete_message')

        msg1 = messages[user.id]
        self.assertPOST200(url, data={'id': msg1.id}, follow=True)
        self.assertDoesNotExist(msg1)

        msg2 = messages[other_user.id]
        self.assertPOST403(url, data={'id': msg2.id}, follow=True)
        self.assertStillExists(msg2)

    def test_merge(self):
        def creator(contact01, contact02):
            priority = UserMessagePriority.objects.create(title='Important')
            user1 = self.create_user(0)
            self._create_usermessage(
                'Beware',
                'This guy wants to fight against you',
                priority, [user1], contact01,
            )
            self._create_usermessage(
                'Oh',
                'This guy wants to meet you',
                priority, [user1], contact02,
            )
            self.assertEqual(2, UserMessage.objects.count())

        def assertor(contact01):
            messages = UserMessage.objects.all()
            self.assertEqual(2, len(messages))

            for msg in messages:
                self.assertEqual(contact01, msg.real_entity)

        self.aux_test_merge(creator, assertor, moved_count=0)

    def test_delete_priority01(self):
        priority = UserMessagePriority.objects.create(title='Important')
        response = self.client.post(reverse(
            'creme_config__delete_instance',
            args=('assistants', 'message_priority', priority.id),
        ))
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(UserMessagePriority).job
        job.type.execute(job)
        self.assertDoesNotExist(priority)

    def test_delete_priority02(self):
        priority = UserMessagePriority.objects.create(title='Important')
        self._create_usermessage('TITLE', 'BODY', priority, [self.user], None)
        self.get_alone_element(UserMessage.objects.all())

        response = self.assertPOST200(reverse(
            'creme_config__delete_instance',
            args=('assistants', 'message_priority', priority.id),
        ))
        self.assertFormError(
            response.context['form'],
            field='replace_assistants__usermessage_priority',
            errors=_('Deletion is not possible.'),
        )

    # def test_job(self):
    #     "Error on email sending."
    #     priority = UserMessagePriority.objects.create(title='Important')
    #     user1 = self.create_user()
    #
    #     self._create_usermessage('TITLE', 'BODY', priority, [user1], None)
    #
    #     self.send_messages_called = False
    #     err_msg = 'Sent error'
    #
    #     def send_messages(this, messages):
    #         self.send_messages_called = True
    #         raise Exception(err_msg)
    #
    #     EmailBackend.send_messages = send_messages
    #
    #     job = self._get_usermessages_job()
    #     usermessages_send_type.execute(job)
    #
    #     self.assertTrue(self.send_messages_called)
    #
    #     message = self.get_alone_element(UserMessage.objects.all())
    #     self.assertTrue(message.email_sent)
    #
    #     jresult = self.get_alone_element(JobResult.objects.filter(job=job))
    #     self.assertListEqual(
    #         [
    #             _('An error occurred while sending emails'),
    #             _('Original error: {}').format(err_msg),
    #         ],
    #         jresult.messages,
    #     )
