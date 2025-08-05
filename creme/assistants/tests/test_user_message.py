from functools import partial

from django.conf import settings
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

    def _create_usermessage(self, *, user,
                            title='Super title', body='content',
                            priority=None, recipients, entity=None,
                            ):
        if priority is None:
            priority = UserMessagePriority.objects.all()[0]

        self.assertNoFormError(self.client.post(
            self._build_add_url(entity),
            data={
                'user':     user.id,
                'title':    title,
                'body':     body,
                'priority': priority.id,
                'users':    [u.id for u in recipients],
            },
        ))

    def test_message_sent_content(self):
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

    @override_settings(SITE_DOMAIN='https://crm.domain')
    def test_message_sent_content__related_entity(self):
        sender = self.get_root_user()
        recipient = self.create_user()
        entity = self.create_entity(user=sender)
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
                'entity': (
                    f'<a href="https://crm.domain{entity.get_absolute_url()}" target="_self">'
                    f'{entity}'
                    f'</a>'
                ),
            },
            content2.get_html_body(user=sender),
        )

    def test_message_sent_content__error(self):
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

    def test_create(self):
        user = self.login_as_assistants_user()
        self.add_credentials(role=user.role, own=['VIEW', 'CHANGE'])
        self.assertFalse(UserMessage.objects.exists())

        queue = get_queue()
        queue.clear()

        entity = self.create_entity(user=user)
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
        recipient = self.create_user(
            username='User01', email='user01@foobar.com', first_name='User01', last_name='Foo',
        )
        self._create_usermessage(
            user=user, title=title, body=body, priority=priority,
            recipients=[recipient], entity=entity,
        )

        message = self.get_alone_element(UserMessage.objects.all())
        self.assertEqual(title,    message.title)
        self.assertEqual(body,     message.body)
        self.assertEqual(priority, message.priority)

        self.assertEqual(entity.id,             message.entity_id)
        self.assertEqual(entity.entity_type_id, message.entity_content_type_id)

        self.assertEqual(user,      message.sender)
        self.assertEqual(recipient, message.recipient)

        self.assertDatetimesAlmostEqual(now(), message.creation_date)

        self.assertEqual(title, str(message))

        notif1 = self.get_object_or_fail(
            Notification,
            user=recipient, channel__uuid=UUID_CHANNEL_USERMESSAGES, output=OUTPUT_WEB,
        )
        self.assertEqual(MessageSentContent.id, notif1.content_id)
        self.assertDictEqual({'instance': message.id}, notif1.content_data)

        self.get_object_or_fail(
            Notification,
            user=recipient, channel__uuid=UUID_CHANNEL_USERMESSAGES, output=OUTPUT_EMAIL,
        )

    @override_settings(SOFTWARE_LABEL='My CRM')
    def test_create__2_users(self):
        user = self.login_as_root_and_get()
        recipient1 = self.create_user(index=0)
        recipient2 = self.create_user(index=1)
        self._create_usermessage(
            user=user, recipients=[recipient1, recipient2],
            entity=self.create_entity(user=user),
        )
        self.assertCountEqual(
            [recipient1, recipient2],
            [msg.recipient for msg in UserMessage.objects.all()],
        )

    def test_create__no_related_entity(self):
        user = self.login_as_root_and_get()
        response = self.assertGET200(self._build_add_url())
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/add-popup.html')

        context = response.context
        self.assertEqual(_('New message'),      context.get('title'))
        self.assertEqual(_('Save the message'), context.get('submit_label'))

        # POST ---
        self._create_usermessage(
            user=user, recipients=[self.create_user(index=0)],
            # entity=None
        )

        message = self.get_alone_element(UserMessage.objects.all())
        self.assertIsNone(message.entity_id)
        self.assertIsNone(message.entity_content_type_id)
        self.assertIsNone(message.real_entity)

    def test_create__1_team(self):
        user = self.login_as_root_and_get()
        teammates = [self.create_user(index=i) for i in range(2)]
        team = self.create_team('Team', *teammates)
        self._create_usermessage(user=user, recipients=[team])
        self.assertCountEqual(teammates, [msg.recipient for msg in UserMessage.objects.all()])

    def test_create__teams(self):
        "Teams and isolated users with non-void intersections."
        user = self.login_as_root_and_get()
        teammates = [self.create_user(index=i) for i in range(4)]

        team1 = self.create_team('Team01', *teammates[:2])
        team2 = self.create_team('Team02', *teammates[1:3])

        self._create_usermessage(
            user=user, recipients=[team1, team2, teammates[0], teammates[3]],
        )
        self.assertCountEqual(
            teammates, [msg.recipient for msg in UserMessage.objects.all()],
        )

    def test_create__no_app_perms(self):
        user = self.login_as_standard()

        response1 = self.assertGET403(
            self._build_add_url(), HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        err = _('You are not allowed to access to the app: {}').format(
            _('Assistants (Todos, Memos, …)')
        )
        self.assertEqual(err, response1.text)

        # ---
        response2 = self.assertGET403(
            self._build_add_url(entity=self.create_entity(user=user)),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(err, response2.text)

    def test_brick(self):
        user = self.login_as_root_and_get()
        other_user = self.create_user()
        priority = UserMessagePriority.objects.first()

        entity1 = self.create_entity(user=user)

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

        response1 = self.assertGET200(entity1.get_absolute_url())
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

    def test_delete_related(self):
        user = self.login_as_root_and_get()
        entity = self.create_entity(user=user)
        self._create_usermessage(user=user, recipients=[self.create_user()], entity=entity)
        message = self.get_alone_element(UserMessage.objects.all())

        entity.delete()
        self.assertDoesNotExist(message)

    def test_delete(self):
        user = self.login_as_assistants_user()
        recipient2 = self.create_user(index=2)

        self._create_usermessage(user=user, recipients=[user, recipient2])

        messages = {msg.recipient_id: msg for msg in UserMessage.objects.all()}
        self.assertEqual(2, len(messages))

        url = reverse('assistants__delete_message')

        msg1 = messages[user.id]
        self.assertPOST200(url, data={'id': msg1.id}, follow=True)
        self.assertDoesNotExist(msg1)

        msg2 = messages[recipient2.id]
        self.assertPOST403(url, data={'id': msg2.id}, follow=True)
        self.assertStillExists(msg2)

    def test_delete__no_app_perm(self):
        user = self.login_as_standard()
        msg = UserMessage.objects.create(
            title='Hi', body='Content', priority=UserMessagePriority.objects.first(),
            sender=user, recipient=user,
            creation_date=now(),
        )
        response = self.assertPOST403(
            reverse('assistants__delete_message'), data={'id': msg.id},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(
            _('You are not allowed to access to the app: {}').format(
                _('Assistants (Todos, Memos, …)')
            ),
            response.text,
        )

    def test_merge(self):
        def creator(user, contact01, contact02):
            priority = UserMessagePriority.objects.create(title='Important')
            user1 = self.create_user(0)
            self._create_usermessage(
                user=user,
                title='Beware',
                body='This guy wants to fight against you',
                priority=priority,
                recipients=[user1],
                entity=contact01,
            )
            self._create_usermessage(
                user=user,
                title='Oh',
                body='This guy wants to meet you',
                priority=priority,
                recipients=[user1],
                entity=contact02,
            )
            self.assertEqual(2, UserMessage.objects.count())

        def assertor(contact01):
            messages = UserMessage.objects.all()
            self.assertEqual(2, len(messages))

            for msg in messages:
                self.assertEqual(contact01, msg.real_entity)

        self.aux_test_merge(creator, assertor, moved_count=0)

    def test_delete_priority(self):
        self.login_as_root()
        priority = UserMessagePriority.objects.create(title='Important')
        self.assertNoFormError(self.client.post(reverse(
            'creme_config__delete_instance',
            args=('assistants', 'message_priority', priority.id),
        )))

        job = self.get_deletion_command_or_fail(UserMessagePriority).job
        job.type.execute(job)
        self.assertDoesNotExist(priority)

    def test_delete_priority__used(self):
        user = self.login_as_root_and_get()
        priority = UserMessagePriority.objects.create(title='Important')
        self._create_usermessage(
            user=user, recipients=[self.create_user()], priority=priority,
        )
        self.get_alone_element(UserMessage.objects.all())

        response = self.assertPOST200(reverse(
            'creme_config__delete_instance',
            args=('assistants', 'message_priority', priority.id),
        ))
        self.assertFormError(
            self.get_form_or_fail(response),
            field='replace_assistants__usermessage_priority',
            errors=_('Deletion is not possible.'),
        )
