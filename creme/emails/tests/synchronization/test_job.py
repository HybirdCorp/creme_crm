import imaplib
import poplib
import socket
from email.headerregistry import Address as EmailAddress
from email.message import EmailMessage
from functools import partial
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from django.conf import settings
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from parameterized import parameterized
from PIL.Image import open as open_img

from creme.creme_core.core.workflow import WorkflowEngine
from creme.creme_core.models import Job, JobResult
from creme.emails.creme_jobs import entity_emails_sync_type
from creme.emails.models import (
    EmailSyncConfigItem,
    EmailToSync,
    EmailToSyncPerson,
)
from creme.emails.tests.base import Contact, Organisation, _EmailsTestCase
from creme.persons.tests.base import (
    skipIfCustomContact,
    skipIfCustomOrganisation,
)


class _SynchronizationJobTestCase(_EmailsTestCase):
    def _get_sync_job(self):
        return self.get_object_or_fail(Job, type_id=entity_emails_sync_type.id)

    def _synchronize_emails(self, job):
        # Empty the Queue to avoid log messages
        WorkflowEngine.get_current()._queue.pickup()

        entity_emails_sync_type.execute(job)


class POPSynchronizationJobTestCase(_SynchronizationJobTestCase):
    @staticmethod
    def create_config_item(user=None, use_ssl=True, port=None):
        return EmailSyncConfigItem.objects.create(
            default_user=user,
            host='pop3.mydomain.org',
            port=port,
            username='spiegel@bebop.org',
            password='$33 yo|_| sp4c3 c0wb0Y',
            use_ssl=use_ssl,
        )

    @staticmethod
    def list_of_bytes(msg_as_str):
        return [s.encode() for s in msg_as_str.split('\n')]

    @classmethod
    def mock_POP_for_messages(cls, *ids_n_messages):
        as_strings = [(msg_id, msg.as_string()) for msg_id, msg in ids_n_messages]

        pop_instance = MagicMock()
        pop_instance.list.return_value = (
            'response',
            [
                # message's ID, message's size
                f'{msg_id} {len(msg_as_str)}'.encode()
                for msg_id, msg_as_str in as_strings
            ],
            # Total size
            sum(len(msg_as_str) for _msg_id, msg_as_str in as_strings),
        )
        pop_instance.retr.side_effect = [
            ('response', cls.list_of_bytes(msg_as_str), len(msg_as_str))
            for _msg_id, msg_as_str in as_strings
        ]

        return pop_instance

    def test_job01(self):
        "No SSL, no message."
        item = EmailSyncConfigItem.objects.create(
            host='pop.mydomain.org',
            username='spike',
            password='c0w|3OY B3b0P',
            port=112,
            use_ssl=False,
        )

        job = self._get_sync_job()
        self.assertIsNone(job.user)

        with patch('poplib.POP3') as pop_mock:
            pop_mock.return_value = pop_instance = self.mock_POP_for_messages()

            # Go !
            self._synchronize_emails(job)

        pop_mock.assert_called_once_with(host=item.host, port=item.port)
        pop_instance.user.assert_called_once_with(item.username)
        pop_instance.pass_.assert_called_once_with(item.password)
        pop_instance.list.assert_called_once()
        pop_instance.quit.assert_called_once()

        self.assertFalse(EmailToSync.objects.all())

        jresult = self.get_alone_element(JobResult.objects.filter(job=job))
        self.assertListEqual(
            [
                _('There was no message on "{host}" for the user "{user}"').format(
                    host=item.host, user=item.username,
                )
            ],
            jresult.messages,
        )

    def test_job02(self):
        "SSL, one message."
        user = self.get_root_user()
        item = EmailSyncConfigItem.objects.create(
            default_user=user,
            host='pop.mydomain.org',
            username='spike',
            password='c0w|3OY B3b0P',
            # port=996,
            use_ssl=True,
        )
        job = self._get_sync_job()

        msg_id = 1
        body = (
            "Hello\n"
            "I'd prefer a blue one.\n"
            "Have a good day."
        )

        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject = 'I want a swordfish II'
        msg['From'] = sender = 'spike@bebop.spc'
        msg['To'] = recipient = 'vicious@reddragons.spc'

        with patch('poplib.POP3_SSL') as pop_mock:
            # Mocking
            pop_mock.return_value = pop_instance = self.mock_POP_for_messages(
                (msg_id, msg),
            )

            # Go!
            self._synchronize_emails(job)

        pop_mock.assert_called_once_with(host=item.host)
        pop_instance.user.assert_called_once_with(item.username)
        pop_instance.pass_.assert_called_once_with(item.password)
        pop_instance.list.assert_called_once()
        pop_instance.retr.assert_called_once_with(msg_id)
        pop_instance.dele.assert_called_once_with(msg_id)

        e2sync = self.get_alone_element(EmailToSync.objects.all())
        self.assertEqual(user,        e2sync.user)
        self.assertEqual(subject,     e2sync.subject)
        self.assertEqual(body + '\n', e2sync.body)
        self.assertEqual('',          e2sync.body_html)
        self.assertIsNone(e2sync.date)

        self.assertCountEqual(
            [
                (EmailToSyncPerson.Type.SENDER,    sender,    None, False),
                (EmailToSyncPerson.Type.RECIPIENT, recipient, None, True),
            ],
            [
                (related.type, related.email, related.person, related.is_main)
                for related in e2sync.related_persons.all()
            ],
        )

        jresult = self.get_alone_element(JobResult.objects.filter(job=job))
        self.assertListEqual(
            [
                ngettext(
                    'There was {count} valid message on "{host}" for the user "{user}"',
                    'There were {count} valid messages on "{host}" for the user "{user}"',
                    1
                ).format(
                    count=1, host=item.host, user=item.username,
                )
            ],
            jresult.messages,
        )

    def test_job03(self):
        "SSL, several messages, long subject."
        user = self.get_root_user()
        item = EmailSyncConfigItem.objects.create(
            default_user=user,
            host='pop3.mydomain.org',
            username='spiegel',
            password='$33 yo|_| sp4c3 c0wb0Y',
            port=995,
            use_ssl=True,
        )
        job = self._get_sync_job()

        msg_id1 = 1
        msg_id2 = 12

        body1 = (
            'Hi\n'
            'I would like a blue one.\n'
            'Have a nice day.\n'
        )
        body_html1 = (
            "<html>"
            "  <head></head>"
            "  <body>"
            "    <p>Hi!</p>"
            "    <p>I would like a <b>blue</b> one.</p>"
            "  </body>"
            "</html>"
        )

        body_html2 = (
            "<html>"
            "  <head></head>"
            "  <body>"
            "    <p>Hello!</p>"
            "    <p>Finally I prefer a <b>green</b> one.</p>"
            "  </body>"
            "</html>"
        )

        msg1 = EmailMessage()
        msg1['From'] = 'spike@bebop.spc'
        msg1['To'] = 'vicious@reddragons.spc'
        msg1['Subject'] = subject1 = 'I want a swordfish' + ' very' * 30 + ' much'
        self.assertGreater(len(subject1), EmailToSync._meta.get_field('subject').max_length)
        msg1.set_content(body1)
        msg1.add_alternative(body_html1, subtype='html')
        # NB: currently integrated images are ignored.
        #  with open("XXX.jpg", 'rb') as img:
        #      msg1.get_payload()[1].add_related(
        #          img.read(), 'image', 'jpeg', cid=img_cid
        #  )
        msg1['Date'] = date1 = self.create_datetime(
            year=2022, month=1, day=10, hour=15, minute=33,
        )

        msg2 = EmailMessage()
        msg2['From'] = 'faye@bebop.spc'
        msg2['To'] = 'julia@reddragons.spc'
        # msg2['Subject'] = 'Color swap'
        # msg2.set_content(...)
        msg2.add_alternative(body_html2, subtype='html')

        with patch('poplib.POP3_SSL') as pop_mock:
            # Mocking
            pop_mock.return_value = pop_instance = self.mock_POP_for_messages(
                (msg_id1, msg1), (msg_id2, msg2),
            )

            # Go !
            self._synchronize_emails(job)

        self.assertListEqual(
            [call(msg_id1), call(msg_id2)],
            pop_instance.retr.call_args_list,
        )

        emails_to_sync = [*EmailToSync.objects.order_by('id')]
        self.assertEqual(2, len(emails_to_sync))

        e2sync1 = emails_to_sync[0]
        self.assertNotEqual(subject1, e2sync1.subject)
        self.assertStartsWith(
            e2sync1.subject, 'I want a swordfish very very very very very very very',
        )
        self.assertEqual(body1, e2sync1.body)
        self.assertHTMLEqual(body_html1, e2sync1.body_html)
        self.assertEqual(date1, e2sync1.date)

        e2sync2 = emails_to_sync[1]
        self.assertEqual('', e2sync2.subject)
        self.assertEqual('', e2sync2.body)
        self.assertHTMLEqual(body_html2, e2sync2.body_html)
        self.assertIsNone(e2sync2.date)

        jresult = self.get_alone_element(JobResult.objects.filter(job=job))
        self.assertListEqual(
            [
                ngettext(
                    'There was {count} valid message on "{host}" for the user "{user}"',
                    'There were {count} valid messages on "{host}" for the user "{user}"',
                    2
                ).format(
                    count=2, host=item.host, user=item.username,
                ),
            ],
            jresult.messages,
        )

    def test_job_assign_user01(self):
        "Use sender & receivers to assign user."
        user1 = self.get_root_user()
        user2 = self.create_user(0)
        user3 = self.create_user(1)

        EmailSyncConfigItem.objects.create(
            default_user=user1,
            host='pop3.mydomain.org',
            username='spiegel',
            password='$33 yo|_| sp4c3 c0wb0Y',
            port=995,
            use_ssl=True,
        )
        job = self._get_sync_job()

        msg1 = EmailMessage()
        msg1['Subject'] = subject1 = 'I want a swordfish'
        msg1['From'] = user2.email
        msg1['To'] = 'notauser@example.org'

        msg2 = EmailMessage()
        msg2['Subject'] = subject2 = 'I want a redtail'
        msg2['From'] = 'whatever@example.org'
        msg2['To'] = user2.email

        msg3 = EmailMessage()
        msg3['Subject'] = subject3 = 'I want a hammerhead'
        msg3['From'] = EmailAddress('Jet Black', 'jblack', 'bebop.mrs')
        msg3['To'] = (
            'donotcare@stuff.com',
            EmailAddress(str(user3.linked_contact), *user3.email.split('@')),
        )

        msg4 = EmailMessage()
        msg4['Subject'] = subject4 = 'Big shot week 12'
        msg4['From'] = EmailAddress('Jet Black', 'jblack', 'bebop.mrs')
        msg4['To'] = 'donotcare1@stuff.com'
        msg4['Cc'] = (
            'donotcare2@stuff.com',
            EmailAddress(str(user3.linked_contact), *user3.email.split('@')),
        )

        msg5 = EmailMessage()
        msg5['Subject'] = subject5 = 'Big shot week 15'
        msg5['From'] = EmailAddress('Jet Black', 'jblack', 'bebop.mrs')
        msg5['To'] = 'donotcare1@stuff.com'
        msg5['Cc'] = 'donotcare2@stuff.com'
        msg5['Bcc'] = (
            'donotcare3@stuff.com',
            EmailAddress(str(user3.linked_contact), *user3.email.split('@')),
        )

        ids_n_messages = [
            (3, msg1), (12, msg2), (25, msg3), (26, msg4), (42, msg5),
        ]

        with patch('poplib.POP3_SSL') as pop_mock:
            # Mocking
            pop_mock.return_value = self.mock_POP_for_messages(*ids_n_messages)

            # Go !
            self._synchronize_emails(job)

        emails_to_sync = [*EmailToSync.objects.order_by('id')]
        self.assertEqual(len(ids_n_messages), len(emails_to_sync))

        e2sync1 = emails_to_sync[0]
        self.assertEqual(subject1, e2sync1.subject)
        self.assertEqual(user2,    e2sync1.user)

        e2sync2 = emails_to_sync[1]
        self.assertEqual(subject2, e2sync2.subject)
        self.assertEqual(user2,    e2sync2.user)

        e2sync3 = emails_to_sync[2]
        self.assertEqual(subject3, e2sync3.subject)
        self.assertEqual(user3,    e2sync3.user)

        e2sync4 = emails_to_sync[3]
        self.assertEqual(subject4, e2sync4.subject)
        self.assertEqual(user3,    e2sync4.user)

        e2sync5 = emails_to_sync[4]
        self.assertEqual(subject5, e2sync5.subject)
        self.assertEqual(user3,    e2sync5.user)

    def test_job_assign_user02(self):
        "Ignore mails when default user is None & not known address is found."
        user = self.get_root_user()

        item = EmailSyncConfigItem.objects.create(
            # default_user=user,
            host='pop3.mydomain.org',
            username='spiegel',
            password='$33 yo|_| sp4c3 c0wb0Y',
            port=995,
            use_ssl=True,
        )
        job = self._get_sync_job()

        msg1 = EmailMessage()
        msg1['Subject'] = 'I want a swordfish'
        msg1['From'] = 'whatever1@example.org'
        msg1['To'] = 'whatever2@example.org'

        msg2 = EmailMessage()
        msg2['Subject'] = subject = 'I want a redtail'
        msg2['From'] = 'whatever3@example.org'
        msg2['To'] = user.email

        with patch('poplib.POP3_SSL') as pop_mock:
            # Mocking
            pop_mock.return_value = pop_instance = self.mock_POP_for_messages(
                (1, msg1), (2, msg2),
            )

            # Go !
            self._synchronize_emails(job)

        pop_instance.list.assert_called_once()
        self.assertEqual(2, pop_instance.retr.call_count)
        self.assertEqual(2, pop_instance.dele.call_count)

        e2sync1 = self.get_alone_element(EmailToSync.objects.all())
        self.assertEqual(subject, e2sync1.subject)
        self.assertEqual(user,    e2sync1.user)

        jresult = self.get_alone_element(JobResult.objects.filter(job=job))
        self.assertListEqual(
            [
                ngettext(
                    'There was {count} valid message on "{host}" for the user "{user}"',
                    'There were {count} valid messages on "{host}" for the user "{user}"',
                    1
                ).format(
                    count=1, host=item.host, user=item.username,
                ),
                ngettext(
                    'There was {count} ignored message (no known address found)',
                    'There were {count} ignored messages (no known address found)',
                    1
                ).format(count=1),
            ],
            jresult.messages,
        )

    def test_job_assign_user__is_staff(self):
        user = self.get_root_user()
        staff_user = self.create_user(index=0, is_staff=True, password='p4$$w0rd')

        EmailSyncConfigItem.objects.create(
            default_user=user,
            host='pop3.mydomain.org',
            username='spiegel',
            password='$33 yo|_| sp4c3 c0wb0Y',
            port=995,
            use_ssl=True,
        )
        job = self._get_sync_job()

        msg1 = EmailMessage()
        msg1['Subject'] = subject = 'I want a swordfish'
        msg1['From'] = staff_user.email
        msg1['To'] = 'whatever2@example.org'

        with patch('poplib.POP3_SSL') as pop_mock:
            # Mocking
            pop_mock.return_value = self.mock_POP_for_messages((1, msg1))

            # Go !
            self._synchronize_emails(job)

        e2sync1 = self.get_alone_element(EmailToSync.objects.all())
        self.assertEqual(subject, e2sync1.subject)
        self.assertEqual(user,    e2sync1.user)

    def test_job_invalid_data01(self):
        "No 'From' => ignored."
        user = self.get_root_user()
        item = EmailSyncConfigItem.objects.create(
            default_user=user,
            host='pop.mydomain.org',
            username='spike',
            password='c0w|3OY B3b0P',
            port=996,
            use_ssl=True,
        )
        job = self._get_sync_job()

        msg = EmailMessage()
        msg.set_content('Hello')
        msg['Subject'] = 'I want a swordfish II'
        # msg['From'] = ...
        msg['To'] = user.email

        with patch('poplib.POP3_SSL') as pop_mock:
            # Mocking
            pop_mock.return_value = pop_instance = self.mock_POP_for_messages((1, msg))

            # Go !
            self._synchronize_emails(job)

        pop_instance.list.assert_called_once()
        pop_instance.retr.assert_called_once()
        pop_instance.dele.assert_called_once()

        self.assertFalse(EmailToSync.objects.all())

        jresult = self.get_alone_element(JobResult.objects.filter(job=job))
        self.assertListEqual(
            [
                ngettext(
                    'There was {count} valid message on "{host}" for the user "{user}"',
                    'There were {count} valid messages on "{host}" for the user "{user}"',
                    0
                ).format(
                    count=0, host=item.host, user=item.username,
                ),
                ngettext(
                    'There was {count} ignored message (no known address found)',
                    'There were {count} ignored messages (no known address found)',
                    1
                ).format(count=1),
            ],
            jresult.messages,
        )

    def test_job_invalid_data02(self):
        "No 'To' => ignored."
        user = self.get_root_user()
        item = self.create_config_item(user)
        job = self._get_sync_job()

        msg = EmailMessage()
        msg.set_content('Hello')
        msg['Subject'] = 'I want a swordfish II'
        msg['From'] = user.email
        # msg['To'] = ...

        with patch('poplib.POP3_SSL') as pop_mock:
            # Mocking
            pop_mock.return_value = pop_instance = self.mock_POP_for_messages((1, msg))

            # Go !
            self._synchronize_emails(job)

        pop_instance.list.assert_called_once()
        pop_instance.retr.assert_called_once()
        pop_instance.dele.assert_called_once()

        self.assertFalse(EmailToSync.objects.all())

        jresult = self.get_alone_element(JobResult.objects.filter(job=job))
        self.assertListEqual(
            [
                ngettext(
                    'There was {count} valid message on "{host}" for the user "{user}"',
                    'There were {count} valid messages on "{host}" for the user "{user}"',
                    0
                ).format(
                    count=0, host=item.host, user=item.username,
                ),
                ngettext(
                    'There was {count} ignored message (no known address found)',
                    'There were {count} ignored messages (no known address found)',
                    1
                ).format(count=1),
            ],
            jresult.messages,
        )

    @skipIfCustomContact
    def test_job_related_persons01(self):
        "Use sender & receivers to assign retrieve Contacts."
        user = self.login_as_emails_user(allowed_apps=['persons'])
        self.add_credentials(user.role, own=['VIEW', 'LINK'])

        create_contact = partial(Contact.objects.create, user=user)
        contact1 = create_contact(
            first_name='Spike', last_name='Spiegel', email='spiegel@bebop.mrs',
        )
        contact2 = create_contact(
            first_name='Jet', last_name='Black', email='jblack@bebop.mrs',
        )

        item = self.create_config_item(user)
        job = self._get_sync_job()

        address3 = 'fvalentine@bebop.mrs'

        msg = EmailMessage()
        msg['Subject'] = 'I want a swordfish'
        msg['From'] = user.email
        msg['To'] = (
            item.username,  # Should be ignored
            contact1.email,
        )
        msg['Cc'] = (
            item.username,  # Should be ignored
            contact2.email,
        )
        msg['Bcc'] = (
            item.username,  # Should be ignored
            address3,  # Not related to an existing Contact
        )

        with patch('poplib.POP3_SSL') as pop_mock:
            # Mocking
            pop_mock.return_value = self.mock_POP_for_messages((1, msg))

            # Go !
            self._synchronize_emails(job)

        e2sync = self.get_alone_element(EmailToSync.objects.order_by('id'))
        self.assertEqual(user, e2sync.user)

        self.assertListEqual(
            [(user.email, user.linked_contact)],
            [
                (person_info.email, person_info.person)
                for person_info in e2sync.related_persons.filter(
                    type=EmailToSyncPerson.Type.SENDER,
                )
            ],
        )

        receivers = {
            person_info.email: person_info
            for person_info in e2sync.related_persons.filter(
                type=EmailToSyncPerson.Type.RECIPIENT,
            )
        }
        self.assertEqual(3, len(receivers))

        receiver1 = receivers.get(contact1.email)
        self.assertIsNotNone(receiver1)
        self.assertEqual(contact1, receiver1.person)
        self.assertTrue(receiver1.is_main)

        receiver2 = receivers.get(contact2.email)
        self.assertIsNotNone(receiver2)
        self.assertEqual(contact2, receiver2.person)
        self.assertFalse(receiver2.is_main)

        receiver3 = receivers.get(address3)
        self.assertIsNotNone(receiver3)
        self.assertIsNone(receiver3.person)

    @skipIfCustomOrganisation
    def test_job_related_persons02(self):
        "Use sender & receivers to assign retrieve Organisations."
        user = self.get_root_user()

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = create_orga(name='Bebop',       email='spiegel@bebop.mrs')
        orga2 = create_orga(name='Mars casino', email='contact@casino.mrs')

        item = self.create_config_item(user)
        job = self._get_sync_job()

        address3 = 'fvalentine@bebop.mrs'

        msg = EmailMessage()
        msg['Subject'] = 'I want a swordfish'
        msg['From'] = orga1.email
        msg['To'] = (
            item.username,  # Should be ignored
            orga2.email,
        )
        msg['Bcc'] = (
            item.username,  # Should be ignored
            address3,  # Not related to an existing Contact/Organisation
        )

        with patch('poplib.POP3_SSL') as pop_mock:
            # Mocking
            pop_mock.return_value = self.mock_POP_for_messages((1, msg))

            # Go !
            self._synchronize_emails(job)

        e2sync = self.get_alone_element(EmailToSync.objects.order_by('id'))
        self.assertEqual(user, e2sync.user)

        self.assertListEqual(
            [(orga1.email, orga1)],
            [
                (person_info.email, person_info.person)
                for person_info in e2sync.related_persons.filter(
                    type=EmailToSyncPerson.Type.SENDER,
                )
            ],
        )

        receivers = {
            person_info.email: person_info.person
            for person_info in e2sync.related_persons.filter(
                type=EmailToSyncPerson.Type.RECIPIENT,
            )
        }
        self.assertEqual(2, len(receivers))
        self.assertEqual(orga2, receivers.get(orga2.email))
        self.assertIsNone(receivers.get(address3, -1))

    @parameterized.expand(['LINK', 'VIEW'])
    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_job_related_persons_credentials01(self, cred):
        "Need VIEW & LINK credentials."
        user = self.login_as_emails_user(allowed_apps=['persons'])
        self.add_credentials(user.role, own=['VIEW', 'LINK'], all=[cred])

        other_user = self.get_root_user()
        contact = Contact.objects.create(
            user=other_user,
            first_name='Spike', last_name='Spiegel', email='spiegel@bebop.mrs',
        )
        orga = Organisation.objects.create(
            user=other_user, name='Bebop', email='contact@bebop.mrs',
        )

        self.create_config_item(user)
        job = self._get_sync_job()

        msg = EmailMessage()
        msg['Subject'] = 'I want a swordfish'
        msg['From'] = contact.email
        msg['To'] = orga.email

        with patch('poplib.POP3_SSL') as pop_mock:
            # Mocking
            pop_mock.return_value = self.mock_POP_for_messages((1, msg))

            # Go !
            self._synchronize_emails(job)

        e2sync = self.get_alone_element(EmailToSync.objects.order_by('id'))
        self.assertEqual(user, e2sync.user)

        self.assertListEqual(
            [(contact.email, None)],
            [
                (person_info.email, person_info.person)
                for person_info in e2sync.related_persons.filter(
                    type=EmailToSyncPerson.Type.SENDER,
                )
            ],
        )
        self.assertListEqual(
            [(orga.email, None)],
            [
                (person_info.email, person_info.person)
                for person_info in e2sync.related_persons.filter(
                    type=EmailToSyncPerson.Type.RECIPIENT,
                )
            ],
        )

    @skipIfCustomOrganisation
    def test_job_related_persons_credentials02(self):
        "Cache per user."
        user = self.login_as_emails_user(allowed_apps=['persons'])
        super_user = self.get_root_user()
        self.add_credentials(user.role, own=['VIEW', 'LINK'])

        recipient_email = 'contact@bebop.mrs'
        create_orga = partial(Organisation.objects.create, email=recipient_email)
        orga1 = create_orga(user=super_user, name='Bebop')
        orga2 = create_orga(user=user, name='Contact Bebop')  # Alphabetically after

        self.create_config_item(user)
        job = self._get_sync_job()

        msg1 = EmailMessage()
        msg1['Subject'] = 'I want a swordfish'
        msg1['From'] = user.email
        msg1['To'] = recipient_email

        msg2 = EmailMessage()
        msg2['Subject'] = 'I want a swordfish too'
        msg2['From'] = super_user.email
        msg2['To'] = recipient_email

        with patch('poplib.POP3_SSL') as pop_mock:
            # Mocking
            pop_mock.return_value = self.mock_POP_for_messages(
                (1, msg1), (2, msg2),
            )

            # Go !
            self._synchronize_emails(job)

        emails_to_sync = [*EmailToSync.objects.order_by('id')]
        self.assertEqual(2, len(emails_to_sync))

        e2sync_1, e2sync_2 = emails_to_sync
        self.assertEqual(user, e2sync_1.user)
        self.assertListEqual(
            [orga2],
            [
                person_info.person
                for person_info in e2sync_1.related_persons.filter(
                    type=EmailToSyncPerson.Type.RECIPIENT,
                )
            ],
        )

        self.assertEqual(super_user, e2sync_2.user)
        self.assertListEqual(
            [orga1],
            [
                person_info.person
                for person_info in e2sync_2.related_persons.filter(
                    type=EmailToSyncPerson.Type.RECIPIENT,
                )
            ],
        )

    @skipIfCustomContact
    def test_job_related_persons__default_owner_is_team(self):
        user = self.login_as_emails_user(allowed_apps=['persons'])
        self.add_credentials(user.role, own=['VIEW', 'LINK'])

        team = self.create_team('Mail owner', user)
        contact = Contact.objects.create(
            user=user, first_name='Spike', last_name='Spiegel', email='spiegel@bebop.mrs',
        )

        self.create_config_item(user=team)
        job = self._get_sync_job()

        from_addr = 'fvalentine@bebop.mrs'

        msg = EmailMessage()
        msg['Subject'] = 'I want a swordfish'
        msg['From'] = from_addr
        msg['To'] = (contact.email,)

        with patch('poplib.POP3_SSL') as pop_mock:
            # Mocking
            pop_mock.return_value = self.mock_POP_for_messages((1, msg))

            # Go !
            self._synchronize_emails(job)

        e2sync = self.get_alone_element(EmailToSync.objects.all())
        self.assertEqual(team, e2sync.user)

        self.assertListEqual(
            [(from_addr, None)],
            [
                (person_info.email, person_info.person)
                for person_info in e2sync.related_persons.filter(
                    type=EmailToSyncPerson.Type.SENDER,
                )
            ],
        )
        self.assertListEqual(
            [(contact.email, contact)],
            [
                (person_info.email, person_info.person)
                for person_info in e2sync.related_persons.filter(
                    type=EmailToSyncPerson.Type.RECIPIENT,
                )
            ],
        )

    def test_job_forwarded_email(self):
        "Only one receiver which is ignored => email is not dropped."
        user = self.get_root_user()

        item = self.create_config_item(user)
        job = self._get_sync_job()

        msg = EmailMessage()
        msg['Subject'] = 'I want a swordfish'
        msg['From'] = user.email
        msg['To'] = item.username

        with patch('poplib.POP3_SSL') as pop_mock:
            # Mocking
            pop_mock.return_value = self.mock_POP_for_messages((1, msg))

            # Go !
            self._synchronize_emails(job)

        e2sync = self.get_alone_element(EmailToSync.objects.order_by('id'))
        self.assertEqual(user, e2sync.user)

        filter_person = e2sync.related_persons.filter
        self.assertListEqual(
            [user.linked_contact],
            [
                person_info.person
                for person_info in filter_person(type=EmailToSyncPerson.Type.SENDER)
            ],
        )
        self.assertFalse([*filter_person(type=EmailToSyncPerson.Type.RECIPIENT)])

    def test_job_attachment01(self):
        "Attachments accepted."
        EmailSyncConfigItem.objects.create(
            default_user=self.create_user(),
            host='pop3.mydomain.org',
            username='spiegel',
            password='$33 yo|_| sp4c3 c0wb0Y',
            port=995,
            use_ssl=True,
            keep_attachments=True,
        )
        job = self._get_sync_job()

        msg = EmailMessage()
        msg['Subject'] = subject = 'I want a swordfish'
        msg['From'] = 'spike@bebop.mrs'
        msg['To'] = 'ed@banana.mrs'

        body = 'Hi\nI would like a yellow one.\nThx.\n'
        msg.set_content(body)

        img_path = Path(settings.CREME_ROOT, 'static', 'chantilly', 'images')
        img_name1 = 'creme_22.png'
        with open(img_path / img_name1, 'rb') as image_file1:
            msg.add_attachment(
                image_file1.read(),
                maintype='image', subtype='png',
                filename=img_name1,
            )
        with open(img_path / 'add_16.png', 'rb') as image_file2:
            msg.add_attachment(
                image_file2.read(),
                maintype='image', subtype='png',
                # filename=...,
            )

        with patch('poplib.POP3_SSL') as pop_mock:
            # Mocking
            pop_mock.return_value = self.mock_POP_for_messages((5, msg))

            # Go !
            self._synchronize_emails(job)

        e2sync = self.get_alone_element(EmailToSync.objects.all())
        self.assertEqual(subject, e2sync.subject)
        self.assertEqual(body,    e2sync.body)
        self.assertEqual('',      e2sync.body_html)

        attachments = [*e2sync.attachments.all()]
        self.assertEqual(2, len(attachments))

        file_ref1 = attachments[0]
        self.assertIsNone(file_ref1.user)
        self.assertFalse(file_ref1.temporary)
        self.assertEqual(img_name1, file_ref1.basename)

        path1 = Path(file_ref1.filedata.path)
        self.assertStartsWith(path1.name, 'creme_22')

        with open_img(path1) as img:
            self.assertTupleEqual((22, 22), img.size)

        file_ref2 = attachments[1]
        self.assertEqual('untitled_attachment_1', file_ref2.basename)

        with open_img(file_ref2.filedata.path) as img:
            self.assertTupleEqual((16, 16), img.size)

    def test_job_attachment02(self):
        "Attachments not accepted."
        EmailSyncConfigItem.objects.create(
            default_user=self.get_root_user(),
            host='pop3.mydomain.org',
            username='spiegel',
            password='$33 yo|_| sp4c3 c0wb0Y',
            port=995,
            use_ssl=True,
            keep_attachments=False,
        )
        job = self._get_sync_job()

        msg = EmailMessage()
        msg['Subject'] = subject = 'I want a swordfish'
        msg['From'] = 'spike@bebop.spc'
        msg['To'] = 'ed@spacemotor.mrs'
        msg.set_content('Hi\nI would like a yellow one.\nThx.\n')

        with open(
            Path(settings.CREME_ROOT, 'static', 'chantilly', 'images', 'creme_22.png'),
            'rb',
        ) as image_file:
            img_data = image_file.read()

        msg.add_attachment(
            img_data, maintype='image', subtype='png', filename='creme_22.png',
        )

        with patch('poplib.POP3_SSL') as pop_mock:
            # Mocking
            pop_mock.return_value = self.mock_POP_for_messages((1, msg))

            # Go !
            self._synchronize_emails(job)

        e2sync = self.get_alone_element(EmailToSync.objects.all())
        self.assertEqual(subject, e2sync.subject)
        self.assertFalse(e2sync.attachments.all())

    def test_job_error01(self):
        "Error when instancing the POP class."
        item = self.create_config_item(use_ssl=False)

        job = self._get_sync_job()
        error_msg = 'Unit test error'

        with patch('poplib.POP3') as pop_mock:
            pop_mock.side_effect = poplib.error_proto(error_msg)

            self._synchronize_emails(job)

        self.assertFalse(EmailToSync.objects.all())

        jresult = self.get_alone_element(JobResult.objects.filter(job=job))
        self.assertListEqual(
            [
                _(
                    'Error while retrieving emails on "{host}" for the user "{user}" '
                    '[original error: {error}]'
                ).format(host=item.host, user=item.username, error=error_msg),
            ],
            jresult.messages,
        )

    def test_job_error02(self):
        "Error when retrieving list."
        item = self.create_config_item(use_ssl=False, port=112)

        job = self._get_sync_job()
        error_msg = 'Unit test error (list)'

        with patch('poplib.POP3') as pop_mock:
            # Mocking
            pop_instance = MagicMock()
            pop_instance.list.side_effect = poplib.error_proto(error_msg)

            pop_mock.return_value = pop_instance

            # Go !
            self._synchronize_emails(job)

        pop_mock.assert_called_once_with(host=item.host, port=item.port)
        pop_instance.user.assert_called_once_with(item.username)
        pop_instance.pass_.assert_called_once_with(item.password)
        pop_instance.list.assert_called_once()
        pop_instance.quit.assert_called_once()
        self.assertFalse(pop_instance.retr.call_count)
        self.assertFalse(pop_instance.dele.call_count)

        self.assertFalse(EmailToSync.objects.all())

        jresult = self.get_alone_element(JobResult.objects.filter(job=job))
        self.assertListEqual(
            # TODO?
            # [
            #     _(
            #         'Error while retrieving emails on "{host}" for the user "{user}" '
            #         '[original error: {error}]'
            #     ).format(host=item.host, user=item.username, error=error_msg)
            # ],
            [
                _('There was no message on "{host}" for the user "{user}"').format(
                    host=item.host, user=item.username,
                )
            ],
            jresult.messages,
        )

    def test_job_error03(self):
        "Error with some messages."
        item = self.create_config_item(user=self.get_root_user(), use_ssl=False)
        job = self._get_sync_job()

        msg_id1 = 12
        msg_id2 = 25

        msg2 = EmailMessage()
        # msg2.set_content(body)
        msg2['Subject'] = subject = 'I want a hammerhead'
        msg2['From'] = 'spike@bebop.spc'
        msg2['To'] = 'ed@spacemotor.mrs'

        msg_as_str2 = msg2.as_string()

        with patch('poplib.POP3') as pop_mock:
            # Mocking
            pop_instance = MagicMock()
            pop_instance.list.return_value = (
                'response',
                [
                    b'notint 123',
                    f'{msg_id1} 123'.encode(),
                    f'{msg_id2} {len(msg_as_str2)}'.encode(),
                ],  # messages
                len(msg_as_str2),  # total size
            )
            pop_instance.retr.side_effect = [
                poplib.error_proto('Invalid ID'),
                ('response', self.list_of_bytes(msg_as_str2), len(msg_as_str2)),
            ]
            pop_instance.dele.side_effect = poplib.error_proto('I am tired')
            pop_instance.quit.side_effect = socket.error('I am tired too')

            pop_mock.return_value = pop_instance

            # Go !
            self._synchronize_emails(job)

        pop_instance.dele.assert_called_once_with(msg_id2)
        pop_instance.quit.assert_called_once()

        e2sync1 = self.get_alone_element(EmailToSync.objects.all())
        self.assertEqual(subject, e2sync1.subject)
        self.assertEqual('',      e2sync1.body)

        jresult = self.get_alone_element(JobResult.objects.filter(job=job))
        self.assertListEqual(
            [
                ngettext(
                    'There was {count} valid message on "{host}" for the user "{user}"',
                    'There were {count} valid messages on "{host}" for the user "{user}"',
                    1
                ).format(count=1, host=item.host, user=item.username),
                ngettext(
                    'There was {count} erroneous message (see logs for more details)',
                    'There were {count} erroneous messages (see logs for more details)',
                    2
                ).format(count=2),
            ],
            jresult.messages,
        )


class IMAPSynchronizationJobTestCase(_SynchronizationJobTestCase):
    @staticmethod
    def create_config_item(user=None, use_ssl=True):
        return EmailSyncConfigItem.objects.create(
            default_user=user,
            type=EmailSyncConfigItem.Type.IMAP,
            host='imap.mydomain.org',
            username='spiegel',
            password='$33 yo|_| sp4c3 c0wb0Y',
            use_ssl=use_ssl,
        )

    @staticmethod
    def mock_IMAP_for_messages(*ids_n_messages):
        imap_instance = MagicMock()
        imap_instance.select.return_value = ('OK', [b'%i' % len(ids_n_messages)])

        imap_instance.search.return_value = (
            'OK',
            [b' '.join(msg_id for msg_id, _msg in ids_n_messages)],
        )
        imap_instance.fetch.side_effect = [
            (
                'OK',
                [(
                    br'%b (FLAGS (\Seen \Recent) RFC822 {7167}' % msg_id,
                    msg.as_bytes(),
                    b')'
                )],
            ) for msg_id, msg in ids_n_messages
        ]

        return imap_instance

    def test_job01(self):
        "No SSL, no message."
        item = EmailSyncConfigItem.objects.create(
            type=EmailSyncConfigItem.Type.IMAP,
            host='imap.mydomain.org',
            username='spike',
            password='c0w|3OY B3b0P',
            port=112,
            use_ssl=False,
        )

        job = self._get_sync_job()
        self.assertIsNone(job.user)

        with patch('imaplib.IMAP4') as imap_mock:
            # Mocking
            imap_mock.return_value = imap_instance = self.mock_IMAP_for_messages()

            # Go !
            self._synchronize_emails(job)

        imap_mock.assert_called_once_with(host=item.host, port=item.port)
        imap_instance.login.assert_called_once_with(item.username, item.password)
        imap_instance.select.assert_called_once()
        self.assertFalse(imap_instance.search.call_count)
        # self.assertFalse(imap_instance.expunge.call_count) TODO?
        imap_instance.expunge.assert_called_once()
        imap_instance.close.assert_called_once()
        imap_instance.logout.assert_called_once()

        self.assertFalse(EmailToSync.objects.all())

        jresult = self.get_alone_element(JobResult.objects.filter(job=job))
        self.assertListEqual(
            [
                _('There was no message on "{host}" for the user "{user}"').format(
                    host=item.host, user=item.username,
                )
            ],
            jresult.messages,
        )

    def test_job02(self):
        "SSL, one message."
        user = self.get_root_user()
        item = EmailSyncConfigItem.objects.create(
            type=EmailSyncConfigItem.Type.IMAP,
            default_user=user,
            host='imap.mydomain.org',
            username='spike',
            password='c0w|3OY B3b0P',
            port=996,
            use_ssl=True,
        )
        job = self._get_sync_job()

        msg_id = b'1'
        body = (
            "Hello\n"
            "I'd prefer a blue one.\n"
            "Have a good day."
        )

        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject = 'I want a swordfish II'
        msg['From'] = sender = 'spike@bebop.spc'
        msg['To'] = recipient = 'vicious@reddragons.spc'

        with patch('imaplib.IMAP4_SSL') as imap_mock:
            # Mocking
            imap_mock.return_value = imap_instance = self.mock_IMAP_for_messages((msg_id, msg))

            # Go!
            self._synchronize_emails(job)

        imap_mock.assert_called_once_with(host=item.host, port=item.port)
        imap_instance.login.assert_called_once_with(item.username, item.password)
        imap_instance.search.assert_called_once()
        imap_instance.fetch.assert_called_once_with(msg_id, '(RFC822)')
        imap_instance.store.assert_called_once_with(msg_id, '+FLAGS', r'\Deleted')
        imap_instance.expunge.assert_called_once()

        e2sync = self.get_alone_element(EmailToSync.objects.all())
        self.assertEqual(user,        e2sync.user)
        self.assertEqual(subject,     e2sync.subject)
        self.assertEqual(body + '\n', e2sync.body)
        self.assertEqual('',          e2sync.body_html)
        self.assertIsNone(e2sync.date)

        self.assertCountEqual(
            [
                (EmailToSyncPerson.Type.SENDER,    sender,    None, False),
                (EmailToSyncPerson.Type.RECIPIENT, recipient, None, True),
            ],
            [
                (related.type, related.email, related.person, related.is_main)
                for related in e2sync.related_persons.all()
            ],
        )

        jresult = self.get_alone_element(JobResult.objects.filter(job=job))
        self.assertListEqual(
            [
                ngettext(
                    'There was {count} valid message on "{host}" for the user "{user}"',
                    'There were {count} valid messages on "{host}" for the user "{user}"',
                    1
                ).format(
                    count=1, host=item.host, user=item.username,
                )
            ],
            jresult.messages,
        )

    def test_job03(self):
        "POP, SSL, several messages."
        user = self.get_root_user()
        item = EmailSyncConfigItem.objects.create(
            type=EmailSyncConfigItem.Type.IMAP,
            default_user=user,
            host='imap.mydomain.org',
            username='spiegel',
            password='$33 yo|_| sp4c3 c0wb0Y',
            port=995,
            use_ssl=True,
        )
        job = self._get_sync_job()

        msg_id1 = b'1'
        msg_id2 = b'12'

        body1 = (
            'Hi\n'
            'I would like a blue one.\n'
            'Have a nice day.\n'
        )
        body_html1 = (
            "<html>"
            "  <head></head>"
            "  <body>"
            "    <p>Hi!</p>"
            "    <p>I would like a <b>blue</b> one.</p>"
            "  </body>"
            "</html>"
        )

        body_html2 = (
            "<html>"
            "  <head></head>"
            "  <body>"
            "    <p>Hello!</p>"
            "    <p>Finally I prefer a <b>green</b> one.</p>"
            "  </body>"
            "</html>"
        )

        msg1 = EmailMessage()
        msg1['From'] = 'spike@bebop.spc'
        msg1['To'] = 'vicious@reddragons.spc'
        msg1['Subject'] = subject1 = 'I want a swordfish' + ' very' * 30 + ' much'
        self.assertGreater(len(subject1), EmailToSync._meta.get_field('subject').max_length)
        msg1.set_content(body1)
        msg1.add_alternative(body_html1, subtype='html')
        # NB: currently integrated images are ignored.
        #  with open("XXX.jpg", 'rb') as img:
        #      msg1.get_payload()[1].add_related(
        #          img.read(), 'image', 'jpeg', cid=img_cid
        #  )
        msg1['Date'] = date1 = self.create_datetime(
            year=2022, month=1, day=10, hour=15, minute=33,
        )

        msg2 = EmailMessage()
        msg2['From'] = 'faye@bebop.spc'
        msg2['To'] = 'julia@reddragons.spc'
        # msg2['Subject'] = 'Color swap'
        # msg2.set_content(...)
        msg2.add_alternative(body_html2, subtype='html')

        with patch('imaplib.IMAP4_SSL') as imap_mock:
            # Mocking
            imap_mock.return_value = imap_instance = self.mock_IMAP_for_messages(
                (msg_id1, msg1), (msg_id2, msg2),
            )

            # Go !
            self._synchronize_emails(job)

        self.assertListEqual(
            [call(msg_id1, '(RFC822)'), call(msg_id2, '(RFC822)')],
            imap_instance.fetch.call_args_list,
        )

        emails_to_sync = [*EmailToSync.objects.order_by('id')]
        self.assertEqual(2, len(emails_to_sync))

        e2sync1 = emails_to_sync[0]
        self.assertNotEqual(subject1, e2sync1.subject)
        self.assertStartsWith(
            e2sync1.subject, 'I want a swordfish very very very very very very very',
        )
        self.assertEqual(body1, e2sync1.body)
        self.assertHTMLEqual(body_html1, e2sync1.body_html)
        self.assertEqual(date1, e2sync1.date)

        e2sync2 = emails_to_sync[1]
        self.assertEqual('', e2sync2.subject)
        self.assertEqual('', e2sync2.body)
        self.assertHTMLEqual(body_html2, e2sync2.body_html)
        self.assertIsNone(e2sync2.date)

        jresult = self.get_alone_element(JobResult.objects.filter(job=job))
        self.assertListEqual(
            [
                ngettext(
                    'There was {count} valid message on "{host}" for the user "{user}"',
                    'There were {count} valid messages on "{host}" for the user "{user}"',
                    2
                ).format(
                    count=2, host=item.host, user=item.username,
                ),
            ],
            jresult.messages,
        )

    def test_job_assign_user01(self):
        "Use sender & receivers to assign user."
        user1 = self.get_root_user()
        user2 = self.create_user(0)
        user3 = self.create_user(1)

        EmailSyncConfigItem.objects.create(
            type=EmailSyncConfigItem.Type.IMAP,
            default_user=user1,
            host='impa4.mydomain.org',
            username='spiegel',
            password='$33 yo|_| sp4c3 c0wb0Y',
            port=995,
            use_ssl=True,
        )
        job = self._get_sync_job()

        msg1 = EmailMessage()
        msg1['Subject'] = subject1 = 'I want a swordfish'
        msg1['From'] = user2.email
        msg1['To'] = 'notauser@example.org'

        msg2 = EmailMessage()
        msg2['Subject'] = subject2 = 'I want a redtail'
        msg2['From'] = 'whatever@example.org'
        msg2['To'] = user2.email

        msg3 = EmailMessage()
        msg3['Subject'] = subject3 = 'I want a hammerhead'
        msg3['From'] = EmailAddress('Jet Black', 'jblack', 'bebop.mrs')
        msg3['To'] = (
            'donotcare@stuff.com',
            EmailAddress(str(user3.linked_contact), *user3.email.split('@')),
        )

        msg4 = EmailMessage()
        msg4['Subject'] = subject4 = 'Big shot week 12'
        msg4['From'] = EmailAddress('Jet Black', 'jblack', 'bebop.mrs')
        msg4['To'] = 'donotcare1@stuff.com'
        msg4['Cc'] = (
            'donotcare2@stuff.com',
            EmailAddress(str(user3.linked_contact), *user3.email.split('@')),
        )

        msg5 = EmailMessage()
        msg5['Subject'] = subject5 = 'Big shot week 15'
        msg5['From'] = EmailAddress('Jet Black', 'jblack', 'bebop.mrs')
        msg5['To'] = 'donotcare1@stuff.com'
        msg5['Cc'] = 'donotcare2@stuff.com'
        msg5['Bcc'] = (
            'donotcare3@stuff.com',
            EmailAddress(str(user3.linked_contact), *user3.email.split('@')),
        )

        ids_n_messages = [
            (b'1', msg1), (b'3', msg2), (b'6', msg3), (b'12', msg4), (b'22', msg5),
        ]

        with patch('imaplib.IMAP4_SSL') as pop_mock:
            # Mocking
            pop_mock.return_value = self.mock_IMAP_for_messages(*ids_n_messages)

            # Go !
            self._synchronize_emails(job)

        emails_to_sync = [*EmailToSync.objects.order_by('id')]
        self.assertEqual(len(ids_n_messages), len(emails_to_sync))

        e2sync1 = emails_to_sync[0]
        self.assertEqual(subject1, e2sync1.subject)
        self.assertEqual(user2,    e2sync1.user)

        e2sync2 = emails_to_sync[1]
        self.assertEqual(subject2, e2sync2.subject)
        self.assertEqual(user2,    e2sync2.user)

        e2sync3 = emails_to_sync[2]
        self.assertEqual(subject3, e2sync3.subject)
        self.assertEqual(user3,    e2sync3.user)

        e2sync4 = emails_to_sync[3]
        self.assertEqual(subject4, e2sync4.subject)
        self.assertEqual(user3,    e2sync4.user)

        e2sync5 = emails_to_sync[4]
        self.assertEqual(subject5, e2sync5.subject)
        self.assertEqual(user3,    e2sync5.user)

    def test_job_assign_user02(self):
        "Ignore mails when default user is None & not known address is found."
        user = self.get_root_user()

        item = EmailSyncConfigItem.objects.create(
            # default_user=user,
            type=EmailSyncConfigItem.Type.IMAP,
            host='imap-bebop.mydomain.org',
            username='spiegel',
            password='$33 yo|_| sp4c3 c0wb0Y',
            port=995,
            use_ssl=True,
        )
        job = self._get_sync_job()

        msg1 = EmailMessage()
        msg1['Subject'] = 'I want a swordfish'
        msg1['From'] = 'whatever1@example.org'
        msg1['To'] = 'whatever2@example.org'

        msg2 = EmailMessage()
        msg2['Subject'] = subject = 'I want a redtail'
        msg2['From'] = 'whatever3@example.org'
        msg2['To'] = user.email

        messages = [(b'1', msg1), (b'2', msg2)]

        with patch('imaplib.IMAP4_SSL') as imap_mock:
            # Mocking
            imap_mock.return_value = imap_instance = self.mock_IMAP_for_messages(*messages)

            # Go !
            self._synchronize_emails(job)

        imap_instance.search.assert_called_once()
        self.assertEqual(2, imap_instance.fetch.call_count)
        self.assertEqual(2, imap_instance.store.call_count)

        e2sync1 = self.get_alone_element(EmailToSync.objects.all())
        self.assertEqual(subject, e2sync1.subject)
        self.assertEqual(user,    e2sync1.user)

        jresult = self.get_alone_element(JobResult.objects.filter(job=job))
        self.assertListEqual(
            [
                ngettext(
                    'There was {count} valid message on "{host}" for the user "{user}"',
                    'There were {count} valid messages on "{host}" for the user "{user}"',
                    1
                ).format(
                    count=1, host=item.host, user=item.username,
                ),
                ngettext(
                    'There was {count} ignored message (no known address found)',
                    'There were {count} ignored messages (no known address found)',
                    1
                ).format(count=1),
            ],
            jresult.messages,
        )

    def test_job_invalid_data01(self):
        "No 'From' => ignored."
        user = self.get_root_user()
        item = EmailSyncConfigItem.objects.create(
            default_user=user,
            type=EmailSyncConfigItem.Type.IMAP,
            host='pop.mydomain.org',
            username='spike',
            password='c0w|3OY B3b0P',
            port=996,
            use_ssl=True,
        )
        job = self._get_sync_job()

        msg = EmailMessage()
        msg.set_content('Hello')
        msg['Subject'] = 'I want a swordfish II'
        # msg['From'] = ...
        msg['To'] = user.email

        with patch('imaplib.IMAP4_SSL') as pop_mock:
            # Mocking
            pop_mock.return_value = imap_instance = self.mock_IMAP_for_messages((b'1', msg))

            # Go !
            self._synchronize_emails(job)

        imap_instance.search.assert_called_once()
        imap_instance.fetch.assert_called_once()
        imap_instance.store.assert_called_once()

        self.assertFalse(EmailToSync.objects.all())

        jresult = self.get_alone_element(JobResult.objects.filter(job=job))
        self.assertListEqual(
            [
                ngettext(
                    'There was {count} valid message on "{host}" for the user "{user}"',
                    'There were {count} valid messages on "{host}" for the user "{user}"',
                    0
                ).format(
                    count=0, host=item.host, user=item.username,
                ),
                ngettext(
                    'There was {count} ignored message (no known address found)',
                    'There were {count} ignored messages (no known address found)',
                    1
                ).format(count=1),
            ],
            jresult.messages,
        )

    def test_job_invalid_data02(self):
        "No 'To' => ignored."
        user = self.get_root_user()
        item = self.create_config_item(user)
        job = self._get_sync_job()

        msg = EmailMessage()
        msg.set_content('Hello')
        msg['Subject'] = 'I want a swordfish II'
        msg['From'] = user.email
        # msg['To'] = ...

        with patch('imaplib.IMAP4_SSL') as imap_mock:
            # Mocking
            imap_mock.return_value = imap_instance = self.mock_IMAP_for_messages((b'2', msg))

            # Go !
            self._synchronize_emails(job)

        imap_instance.search.assert_called_once()
        imap_instance.fetch.assert_called_once()
        imap_instance.store.assert_called_once()

        self.assertFalse(EmailToSync.objects.all())

        jresult = self.get_alone_element(JobResult.objects.filter(job=job))
        self.assertListEqual(
            [
                ngettext(
                    'There was {count} valid message on "{host}" for the user "{user}"',
                    'There were {count} valid messages on "{host}" for the user "{user}"',
                    0
                ).format(
                    count=0, host=item.host, user=item.username,
                ),
                ngettext(
                    'There was {count} ignored message (no known address found)',
                    'There were {count} ignored messages (no known address found)',
                    1
                ).format(count=1),
            ],
            jresult.messages,
        )

    @skipIfCustomContact
    def test_job_related_persons01(self):
        "Use sender & receivers to assign retrieve Contacts."
        user = self.login_as_emails_user(allowed_apps=['persons'])
        self.add_credentials(user.role, own=['VIEW', 'LINK'])

        create_contact = partial(Contact.objects.create, user=user)
        contact1 = create_contact(
            first_name='Spike', last_name='Spiegel', email='spiegel@bebop.mrs',
        )
        contact2 = create_contact(
            first_name='Jet', last_name='Black', email='jblack@bebop.mrs',
        )

        item = self.create_config_item(user)
        job = self._get_sync_job()

        address3 = 'fvalentine@bebop.mrs'

        msg = EmailMessage()
        msg['Subject'] = 'I want a swordfish'
        msg['From'] = user.email
        msg['To'] = (
            item.username,  # Should be ignored
            contact1.email,
        )
        msg['Cc'] = (
            item.username,  # Should be ignored
            contact2.email,
        )
        msg['Bcc'] = (
            item.username,  # Should be ignored
            address3,  # Not related to an existing Contact
        )

        with patch('imaplib.IMAP4_SSL') as imap_mock:
            # Mocking
            imap_mock.return_value = self.mock_IMAP_for_messages((b'1', msg))

            # Go !
            self._synchronize_emails(job)

        e2sync = self.get_alone_element(EmailToSync.objects.order_by('id'))
        self.assertEqual(user, e2sync.user)

        self.assertListEqual(
            [(user.email, user.linked_contact)],
            [
                (person_info.email, person_info.person)
                for person_info in e2sync.related_persons.filter(
                    type=EmailToSyncPerson.Type.SENDER,
                )
            ],
        )

        receivers = {
            person_info.email: person_info
            for person_info in e2sync.related_persons.filter(
                type=EmailToSyncPerson.Type.RECIPIENT,
            )
        }
        self.assertEqual(3, len(receivers))

        receiver1 = receivers.get(contact1.email)
        self.assertIsNotNone(receiver1)
        self.assertEqual(contact1, receiver1.person)
        self.assertTrue(receiver1.is_main)

        receiver2 = receivers.get(contact2.email)
        self.assertIsNotNone(receiver2)
        self.assertEqual(contact2, receiver2.person)
        self.assertFalse(receiver2.is_main)

        receiver3 = receivers.get(address3)
        self.assertIsNotNone(receiver3)
        self.assertIsNone(receiver3.person)

    @skipIfCustomOrganisation
    def test_job_related_persons02(self):
        "Use sender & receivers to assign retrieve Organisations."
        user = self.get_root_user()

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = create_orga(name='Bebop',       email='spiegel@bebop.mrs')
        orga2 = create_orga(name='Mars casino', email='contact@casino.mrs')

        item = self.create_config_item(user)
        job = self._get_sync_job()

        address3 = 'fvalentine@bebop.mrs'

        msg = EmailMessage()
        msg['Subject'] = 'I want a swordfish'
        msg['From'] = orga1.email
        msg['To'] = (
            item.username,  # Should be ignored
            orga2.email,
        )
        msg['Bcc'] = (
            item.username,  # Should be ignored
            address3,  # Not related to an existing Contact/Organisation
        )

        with patch('imaplib.IMAP4_SSL') as imap_mock:
            # Mocking
            imap_mock.return_value = self.mock_IMAP_for_messages((b'1', msg))

            # Go !
            self._synchronize_emails(job)

        e2sync = self.get_alone_element(EmailToSync.objects.order_by('id'))
        self.assertEqual(user, e2sync.user)

        self.assertListEqual(
            [(orga1.email, orga1)],
            [
                (person_info.email, person_info.person)
                for person_info in e2sync.related_persons.filter(
                    type=EmailToSyncPerson.Type.SENDER,
                )
            ],
        )

        receivers = {
            person_info.email: person_info.person
            for person_info in e2sync.related_persons.filter(
                type=EmailToSyncPerson.Type.RECIPIENT,
            )
        }
        self.assertEqual(2, len(receivers))
        self.assertEqual(orga2, receivers.get(orga2.email))
        self.assertIsNone(receivers.get(address3, -1))

    def test_job_attachment01(self):
        "Attachments accepted."
        EmailSyncConfigItem.objects.create(
            type=EmailSyncConfigItem.Type.IMAP,
            default_user=self.get_root_user(),
            host='pop3.mydomain.org',
            username='spiegel',
            password='$33 yo|_| sp4c3 c0wb0Y',
            port=995,
            use_ssl=True,
            keep_attachments=True,
        )
        job = self._get_sync_job()

        msg = EmailMessage()
        msg['Subject'] = subject = 'I want a swordfish'
        msg['From'] = 'spike@bebop.mrs'
        msg['To'] = 'ed@banana.mrs'

        body = 'Hi\nI would like a yellow one.\nThx.\n'
        msg.set_content(body)

        img_path = Path(settings.CREME_ROOT, 'static', 'chantilly', 'images')
        img_name1 = 'creme_22.png'
        with open(img_path / img_name1, 'rb') as image_file1:
            msg.add_attachment(
                image_file1.read(),
                maintype='image', subtype='png',
                filename=img_name1,
            )
        with open(img_path / 'add_16.png', 'rb') as image_file2:
            msg.add_attachment(
                image_file2.read(),
                maintype='image', subtype='png',
                # filename=...,
            )

        with patch('imaplib.IMAP4_SSL') as pop_mock:
            # Mocking
            pop_mock.return_value = self.mock_IMAP_for_messages((b'2', msg))

            # Go !
            self._synchronize_emails(job)

        e2sync = self.get_alone_element(EmailToSync.objects.all())
        self.assertEqual(subject, e2sync.subject)
        self.assertEqual(body,    e2sync.body)
        self.assertEqual('',      e2sync.body_html)

        attachments = [*e2sync.attachments.all()]
        self.assertEqual(2, len(attachments))

        file_ref1 = attachments[0]
        self.assertIsNone(file_ref1.user)
        self.assertFalse(file_ref1.temporary)
        self.assertEqual(img_name1, file_ref1.basename)

        path1 = Path(file_ref1.filedata.path)
        self.assertStartsWith(path1.name, 'creme_22')

        with open_img(path1) as img:
            self.assertTupleEqual((22, 22), img.size)

        file_ref2 = attachments[1]
        self.assertEqual('untitled_attachment_1', file_ref2.basename)

        with open_img(file_ref2.filedata.path) as img:
            self.assertTupleEqual((16, 16), img.size)

    def test_job_attachment02(self):
        "Attachments not accepted."
        EmailSyncConfigItem.objects.create(
            type=EmailSyncConfigItem.Type.IMAP,
            default_user=self.get_root_user(),
            host='pop3.mydomain.org',
            username='spiegel',
            password='$33 yo|_| sp4c3 c0wb0Y',
            port=995,
            use_ssl=True,
            keep_attachments=False,
        )
        job = self._get_sync_job()

        msg = EmailMessage()
        msg['Subject'] = subject = 'I want a swordfish'
        msg['From'] = 'spike@bebop.spc'
        msg['To'] = 'ed@spacemotor.mrs'
        msg.set_content('Hi\nI would like a yellow one.\nThx.\n')

        with open(
            Path(settings.CREME_ROOT, 'static', 'chantilly', 'images', 'creme_22.png'),
            'rb',
        ) as image_file:
            img_data = image_file.read()

        msg.add_attachment(
            img_data, maintype='image', subtype='png', filename='creme_22.png',
        )

        with patch('imaplib.IMAP4_SSL') as pop_mock:
            # Mocking
            pop_mock.return_value = self.mock_IMAP_for_messages((b'1', msg))

            # Go !
            self._synchronize_emails(job)

        e2sync = self.get_alone_element(EmailToSync.objects.all())
        self.assertEqual(subject, e2sync.subject)
        self.assertFalse(e2sync.attachments.all())

    def test_job_error01(self):
        "Error when instancing the POP class."
        item = self.create_config_item(use_ssl=False)

        job = self._get_sync_job()
        error_msg = 'Unit test error'

        with patch('imaplib.IMAP4.__init__', side_effect=imaplib.IMAP4.error(error_msg)):
            self._synchronize_emails(job)

        self.assertFalse(EmailToSync.objects.all())

        jresult = self.get_alone_element(JobResult.objects.filter(job=job))
        self.assertListEqual(
            [
                _(
                    'Error while retrieving emails on "{host}" for the user "{user}" '
                    '[original error: {error}]'
                ).format(host=item.host, user=item.username, error=error_msg),
            ],
            jresult.messages,
        )

    def test_job_error02(self):
        "Error when retrieving list."
        item = self.create_config_item(use_ssl=False)

        job = self._get_sync_job()
        error_msg = 'Unit test error (search)'

        with patch('imaplib.IMAP4') as imap_mock:
            # Mocking
            imap_instance = MagicMock()
            imap_instance.select.return_value = ('Ok', [b'1'])
            imap_instance.search.side_effect = socket.error(error_msg)
            imap_mock.error = Exception  # TypeError if IMAP4.error is not a BaseException

            imap_mock.return_value = imap_instance

            # Go !
            self._synchronize_emails(job)

        imap_mock.assert_called_once_with(host=item.host)
        imap_instance.search.assert_called_once()
        imap_instance.close.assert_called_once()
        # self.assertFalse(imap_instance.expunge.call_count) TODO?
        imap_instance.expunge.assert_called_once()

        self.assertFalse(EmailToSync.objects.all())

        jresult = self.get_alone_element(JobResult.objects.filter(job=job))
        self.assertListEqual(
            # TODO?
            # [
            #     _(
            #         'Error while retrieving emails on "{host}" for the user "{user}" '
            #         '[original error: {error}]'
            #     ).format(host=item.host, user=item.username, error=error_msg)
            # ],
            [
                _('There was no message on "{host}" for the user "{user}"').format(
                    host=item.host, user=item.username,
                )
            ],
            jresult.messages,
        )

    def test_job_error03(self):
        "Error with some messages."
        item = self.create_config_item(user=self.get_root_user(), use_ssl=False)
        job = self._get_sync_job()

        msg_id1 = b'12'
        msg_id2 = b'25'

        msg2 = EmailMessage()
        # msg2.set_content(body)
        msg2['Subject'] = subject = 'I want a hammerhead'
        msg2['From'] = 'spike@bebop.spc'
        msg2['To'] = 'ed@spacemotor.mrs'

        msg_as_str2 = msg2.as_string()

        with patch('imaplib.IMAP4') as imap_mock:
            # Mocking
            imap_instance = MagicMock()
            imap_instance.select.return_value = ('OK', [b'2'])
            imap_instance.search.return_value = (
                'OK', [b'%b %b' % (msg_id1, msg_id2)]
            )
            imap_instance.fetch.side_effect = [
                socket.error('Invalid ID'),
                (
                    'OK',
                    [(
                        br'%b (FLAGS (\Seen \Recent) RFC822 {7167}' % msg_id2,
                        msg_as_str2.encode(),
                        b')'
                    )],
                ),
            ]

            imap_instance.store.side_effect = socket.error('I am tired')
            imap_instance.logout.side_effect = socket.error('I am tired too')

            imap_mock.return_value = imap_instance
            imap_mock.error = Exception  # TypeError if IMAP4.error is not a BaseException

            # Go !
            self._synchronize_emails(job)

        imap_instance.store.assert_called_once_with(msg_id2, '+FLAGS', r'\Deleted')
        imap_instance.logout.assert_called_once()

        e2sync1 = self.get_alone_element(EmailToSync.objects.all())
        self.assertEqual(subject, e2sync1.subject)
        self.assertEqual('',      e2sync1.body)

        jresult = self.get_alone_element(JobResult.objects.filter(job=job))
        self.assertListEqual(
            [
                ngettext(
                    'There was {count} valid message on "{host}" for the user "{user}"',
                    'There were {count} valid messages on "{host}" for the user "{user}"',
                    1
                ).format(count=1, host=item.host, user=item.username),
                ngettext(
                    'There was {count} erroneous message (see logs for more details)',
                    'There were {count} erroneous messages (see logs for more details)',
                    1
                ).format(count=1),
            ],
            jresult.messages,
        )
