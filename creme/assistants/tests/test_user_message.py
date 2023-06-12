from django.conf import settings
from django.core import mail
from django.core.mail.backends.locmem import EmailBackend
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _

# Should be a test queue
from creme.creme_core.core.job import get_queue
from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickHomeLocation,
    FakeOrganisation,
    Job,
    JobResult,
)
from creme.creme_core.tests.views.base import BrickTestCaseMixin

from ..bricks import UserMessagesBrick
from ..creme_jobs import usermessages_send_type
from ..models import UserMessage, UserMessagePriority
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

    def _get_usermessages_job(self):
        return self.get_object_or_fail(Job, type_id=usermessages_send_type.id)

    def test_populate(self):
        self.assertEqual(3, UserMessagePriority.objects.count())

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
        # user1 = User.objects.create_user(
        #     'User01',
        #     email='user01@foobar.com', first_name='User01', last_name='Foo',
        # )
        user1 = self.create_user(
            username='User01', email='user01@foobar.com', first_name='User01', last_name='Foo',
        )
        self._create_usermessage(title, body, priority, [user1], entity)

        message = self.get_alone_element(UserMessage.objects.all())
        self.assertEqual(title,    message.title)
        self.assertEqual(body,     message.body)
        self.assertEqual(priority, message.priority)

        self.assertFalse(message.email_sent)

        self.assertEqual(entity.id,             message.entity_id)
        self.assertEqual(entity.entity_type_id, message.entity_content_type_id)

        self.assertEqual(self.user, message.sender)
        self.assertEqual(user1,    message.recipient)

        self.assertDatetimesAlmostEqual(now(), message.creation_date)

        self.assertEqual(title, str(message))

        job, _data = self.get_alone_element(queue.refreshed_jobs)
        self.assertEqual(self._get_usermessages_job(), job)

    @override_settings(SOFTWARE_LABEL='My CRM')
    def test_create02(self):
        now_value = now()
        priority = UserMessagePriority.objects.create(title='Important')

        user1 = self.create_user(index=0)
        user2 = self.create_user(index=1)

        job = self._get_usermessages_job()
        self.assertIsNone(job.user)
        self.assertIsNone(job.type.next_wakeup(job, now_value))

        title = 'TITLE'
        body  = 'BODY'
        self._create_usermessage(title, body, priority, [user1, user2], self.entity)

        messages = UserMessage.objects.all()
        self.assertCountEqual([user1, user2], [msg.recipient for msg in messages])

        self.assertIs(now_value, job.type.next_wakeup(job, now_value))

        usermessages_send_type.execute(job)

        messages = mail.outbox
        self.assertEqual(len(messages), 2)

        message = messages[0]
        software = 'My CRM'
        self.assertEqual(
            _('User message from {software}: {title}').format(software=software, title=title),
            message.subject,
        )
        self.assertEqual(
            _('{user} sent you the following message:\n{body}').format(
                user=self.user,
                body=body,
            ),
            message.body,
        )
        self.assertEqual(settings.EMAIL_SENDER, message.from_email)
        self.assertHasNoAttr(message, 'alternatives')
        self.assertFalse(message.attachments)

        for user_msg in UserMessage.objects.all():
            self.assertTrue(user_msg.email_sent)

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
        # self.assertIsNone(message.creme_entity)
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
        entity2 = FakeOrganisation.objects.create(user=user, name='Acme')
        # TODO: deleted entity

        def create_message(entity, title):
            return UserMessage.objects.create(
                title=title,
                body='My body is ready',
                creation_date=now(),
                priority=priority,
                # sender=self.other_user,
                sender=other_user,
                recipient=user,
                # creme_entity=entity,
                real_entity=entity,
            )

        msg1 = create_message(entity1, 'Recall')
        msg2 = create_message(entity1, "It's important")
        msg3 = create_message(entity2, 'Other message')

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

        # ---
        BrickHomeLocation.objects.get_or_create(
            # brick_id=UserMessagesBrick.id_, defaults={'order': 50},
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

    def test_delete_related01(self):
        priority = UserMessagePriority.objects.create(title='Important')
        self._create_usermessage('TITLE', 'BODY', priority, [self.user], self.entity)

        self.assertEqual(1, UserMessage.objects.count())

        self.entity.delete()
        self.assertFalse(UserMessage.objects.all())

    def test_delete(self):
        user = self.user
        # other_user = self.other_user
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
                # self.assertEqual(contact01, msg.creme_entity)
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

    def test_job(self):
        "Error on email sending."
        priority = UserMessagePriority.objects.create(title='Important')
        user1 = self.create_user()

        self._create_usermessage('TITLE', 'BODY', priority, [user1], None)

        self.send_messages_called = False
        err_msg = 'Sent error'

        def send_messages(this, messages):
            self.send_messages_called = True
            raise Exception(err_msg)

        EmailBackend.send_messages = send_messages

        job = self._get_usermessages_job()
        usermessages_send_type.execute(job)

        self.assertTrue(self.send_messages_called)

        message = self.get_alone_element(UserMessage.objects.all())
        self.assertTrue(message.email_sent)

        jresult = self.get_alone_element(JobResult.objects.filter(job=job))
        self.assertListEqual(
            [
                _('An error occurred while sending emails'),
                _('Original error: {}').format(err_msg),
            ],
            jresult.messages,
        )
