import imaplib
import poplib
import socket
from email.message import EmailMessage
from unittest.mock import MagicMock, call, patch

from django.utils.translation import gettext as _

from creme.creme_core.utils.email import IMAPBox, MailBox, POPBox

from ..base import CremeTestCase


class MailBoxTestCase(CremeTestCase):
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

    def test_pop_empty(self):
        host = 'pop.mydomain.org'
        username = 'spike'
        password = 'c0w|3OY B3b0P'
        port = 112
        use_ssl = False

        with patch('poplib.POP3') as pop_mock:
            # Mocking
            pop_mock.return_value = pop_instance = self.mock_POP_for_messages()

            # Go !
            with POPBox(host=host, port=port, use_ssl=use_ssl,
                        username=username, password=password,
                        ) as box:
                email_ids = [*box]

        pop_mock.assert_called_once_with(host=host, port=port)
        pop_instance.user.assert_called_once_with(username)
        pop_instance.pass_.assert_called_once_with(password)
        pop_instance.list.assert_called_once()
        pop_instance.quit.assert_called_once()

        self.assertFalse(email_ids)

    def test_pop_messages(self):
        host = 'pop3.mydomain.org'
        username = 'spiegel'
        password = '$33 yo|_| sp4c3 c0wb0Y'
        use_ssl = True

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
        msg1['Subject'] = 'I want a swordfish'
        msg1.set_content(body1)
        msg1.add_alternative(body_html1, subtype='html')
        msg1['Date'] = self.create_datetime(
            year=2022, month=1, day=10, hour=15, minute=33,
        )

        msg2 = EmailMessage()
        msg2['From'] = 'faye@bebop.spc'
        msg2['To'] = 'julia@reddragons.spc'
        # msg2['Subject'] = 'Color swap'
        # msg2.set_content(...)
        msg2.add_alternative(body_html2, subtype='html')

        email_ids = []
        email_messages = []

        with patch('poplib.POP3_SSL') as pop_mock:
            # Mocking
            pop_mock.return_value = pop_instance = self.mock_POP_for_messages(
                (msg_id1, msg1),
                (msg_id2, msg2),
            )

            # Go
            with POPBox(host=host, use_ssl=use_ssl,  # port=port
                        username=username, password=password,
                        ) as box:
                for email_id in box:
                    email_ids.append(email_id)

                    with box.fetch_email(email_id) as email_message:
                        email_messages.append(email_message)

        self.assertListEqual([msg_id1, msg_id2], email_ids)

        self.assertListEqual(
            [call(msg_id1), call(msg_id2)],
            pop_instance.retr.call_args_list,
        )
        self.assertListEqual(
            [call(msg_id1), call(msg_id2)],
            pop_instance.dele.call_args_list,
        )

        self.assertEqual(2, len(email_messages))

        retr_msg1 = email_messages[0]
        self.assertEqual(msg1['Subject'], retr_msg1['Subject'])
        self.assertEqual(msg1['From'],    retr_msg1['From'])
        self.assertEqual(msg1['To'],      retr_msg1['To'])
        self.assertEqual(msg1['Date'],    retr_msg1['Date'])
        self.assertEqual(body1,          retr_msg1.get_body(('plain',)).get_content())
        self.assertHTMLEqual(body_html1, retr_msg1.get_body(('html',)).get_content())

        retr_msg2 = email_messages[1]
        self.assertIsNone(retr_msg2['Subject'])
        self.assertEqual(msg2['From'], retr_msg2['From'])
        self.assertEqual(msg2['To'],   retr_msg2['To'])
        self.assertEqual(msg2['Date'], retr_msg2['Date'])
        self.assertIsNone(retr_msg2.get_body(('plain',)))
        self.assertHTMLEqual(body_html2, retr_msg2.get_body(('html',)).get_content())

    def test_POP_error01(self):
        "Error when instancing the POP class."
        host = 'pop3.mydomain.org'
        username = 'spiegel'
        error_msg = 'Unit test error'

        with patch('poplib.POP3') as pop_mock:
            # Mocking
            pop_mock.side_effect = poplib.error_proto(error_msg)

            # Go
            with self.assertNoException():
                ctxt = POPBox(
                    host=host, username=username, use_ssl=False, password='password',
                )

            with self.assertRaises(MailBox.Error) as exc_mngr:
                with ctxt:
                    pass

        self.assertEqual(
            _(
                'Error while retrieving emails on "{host}" for the user "{user}" '
                '[original error: {error}]'
            ).format(host=host, user=username, error=error_msg),
            str(exc_mngr.exception),
        )

        self.assertEqual(0, pop_mock.quit.call_count)

    def test_POP_error02(self):
        "Error with some messages."
        msg_id1 = 12
        msg_id2 = 25

        msg2 = EmailMessage()
        msg2['Subject'] = 'I want a hammerhead'
        msg2['From'] = 'spike@bebop.spc'
        msg2['To'] = 'ed@spacemotor.mrs'

        msg_as_str2 = msg2.as_string()
        email_ids = []
        email_messages = []

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
            with POPBox(host='host', use_ssl=False,
                        username='username', password='password',
                        ) as box:
                for email_id in box:
                    email_ids.append(email_id)

                    with box.fetch_email(email_id) as email_message:
                        email_messages.append(email_message)

        pop_instance.dele.assert_called_once_with(msg_id2)
        pop_instance.quit.assert_called_once()

        self.assertListEqual([None, msg_id1, msg_id2], email_ids)

        self.assertEqual(3, len(email_messages))
        self.assertIsNone(email_messages[0])
        self.assertIsNone(email_messages[1])

        retr_msg = email_messages[2]
        self.assertIsInstance(retr_msg, EmailMessage)
        self.assertEqual(msg2['Subject'], retr_msg['Subject'])

    def test_user_error(self):
        "If the user code raise an exception, the related email is not deleted."
        msg_id1 = 8
        msg_id2 = 15

        msg1 = EmailMessage()
        msg1['From'] = 'spike@bebop.spc'
        msg1['To'] = 'vicious@reddragons.spc'
        msg1['Subject'] = 'I want a swordfish'
        msg1.set_content('Hi\n')

        msg2 = EmailMessage()
        msg2['From'] = 'faye@bebop.spc'
        msg2['To'] = 'julia@reddragons.spc'
        msg2['Subject'] = 'Color swap'
        msg1.set_content('How R U?\n')

        with patch('poplib.POP3') as pop_mock:
            # Mocking
            pop_mock.return_value = pop_instance = self.mock_POP_for_messages(
                (msg_id1, msg1),
                (msg_id2, msg2),
            )

            # Go
            with self.assertRaises(ValueError):
                with POPBox(host='pop3.mydomain.org', use_ssl=False,
                            username='spiegel', password='$33 yo|_| sp4c3 c0wb0Y',
                            ) as box:
                    for i, email_id in enumerate(box):
                        with box.fetch_email(email_id):
                            if i:
                                raise ValueError(
                                    'Error in the user code when treating the second message'
                                )

        pop_instance.dele.assert_called_once_with(msg_id1)
        pop_instance.quit.assert_called_once()

    def test_api_error(self):
        "The context managers must be used in a nested way."
        msg = EmailMessage()
        msg['From'] = 'spike@bebop.spc'
        msg['To'] = 'vicious@reddragons.spc'
        msg['Subject'] = 'I want a swordfish'
        msg.set_content('Hi\n')

        with patch('poplib.POP3') as pop_mock:
            # Mocking
            pop_mock.return_value = self.mock_POP_for_messages((8, msg))

            # Go
            with POPBox(host='pop3.mydomain.org', use_ssl=False,
                        username='spiegel', password='$33 yo|_| sp4c3 c0wb0Y',
                        ) as box:
                emails_ids = [*box]

            with self.assertRaises(RuntimeError):
                with box.fetch_email(emails_ids[0]):
                    pass

    def test_imap_empty(self):
        host = 'imap.mydomain.org'
        username = 'spike'
        password = 'c0w|3OY B3b0P'
        port = 112
        use_ssl = False

        with patch('imaplib.IMAP4') as imap_mock:
            # Mocking
            imap_mock.return_value = imap_instance = self.mock_IMAP_for_messages()

            # Go !
            with IMAPBox(host=host, port=port, use_ssl=use_ssl,
                         username=username, password=password,
                         ) as box:
                email_ids = [*box]

        imap_mock.assert_called_once_with(host=host, port=port)
        imap_instance.login.assert_called_once_with(username, password)
        imap_instance.select.assert_called_once()
        self.assertFalse(imap_instance.search.call_count)
        # self.assertFalse(imap_instance.expunge.call_count) TODO?
        imap_instance.expunge.assert_called_once()
        imap_instance.close.assert_called_once()
        imap_instance.logout.assert_called_once()

        self.assertFalse(email_ids)

    def test_imap_messages(self):
        host = 'pop3.mydomain.org'
        username = 'spiegel'
        password = '$33 yo|_| sp4c3 c0wb0Y'
        use_ssl = True

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
        msg1['Subject'] = 'I want a swordfish'
        msg1.set_content(body1)
        msg1.add_alternative(body_html1, subtype='html')
        msg1['Date'] = self.create_datetime(
            year=2022, month=1, day=10, hour=15, minute=33,
        )

        msg2 = EmailMessage()
        msg2['From'] = 'faye@bebop.spc'
        msg2['To'] = 'julia@reddragons.spc'
        # msg2['Subject'] = 'Color swap'
        # msg2.set_content(...)
        msg2.add_alternative(body_html2, subtype='html')

        email_ids = []
        email_messages = []

        with patch('imaplib.IMAP4_SSL') as imap_mock:
            # Mocking
            imap_mock.return_value = imap_instance = self.mock_IMAP_for_messages(
                (msg_id1, msg1),
                (msg_id2, msg2),
            )

            # Go
            with IMAPBox(host=host, use_ssl=use_ssl,  # port=port
                         username=username, password=password,
                         ) as box:
                for email_id in box:
                    email_ids.append(email_id)

                    with box.fetch_email(email_id) as email_message:
                        email_messages.append(email_message)

        self.assertListEqual([msg_id1, msg_id2], email_ids)

        self.assertListEqual(
            [call(msg_id1, '(RFC822)'), call(msg_id2, '(RFC822)')],
            imap_instance.fetch.call_args_list,
        )

        self.assertEqual(2, len(email_messages))

        retr_msg1 = email_messages[0]
        self.assertEqual(msg1['Subject'], retr_msg1['Subject'])
        self.assertEqual(msg1['From'],    retr_msg1['From'])
        self.assertEqual(msg1['To'],      retr_msg1['To'])
        self.assertEqual(msg1['Date'],    retr_msg1['Date'])
        self.assertEqual(body1,          retr_msg1.get_body(('plain',)).get_content())
        self.assertHTMLEqual(body_html1, retr_msg1.get_body(('html',)).get_content())

        retr_msg2 = email_messages[1]
        self.assertIsNone(retr_msg2['Subject'])
        self.assertEqual(msg2['From'], retr_msg2['From'])
        self.assertEqual(msg2['To'],   retr_msg2['To'])
        self.assertEqual(msg2['Date'], retr_msg2['Date'])
        self.assertIsNone(retr_msg2.get_body(('plain',)))
        self.assertHTMLEqual(body_html2, retr_msg2.get_body(('html',)).get_content())

    def test_IMAP_error01(self):
        "Error when instancing the IMAP4 class."
        host = 'impa4.mydomain.org'
        username = 'spiegel'
        error_msg = 'Unit test error'

        with patch('imaplib.IMAP4.__init__', side_effect=imaplib.IMAP4.error(error_msg)):
            with self.assertNoException():
                ctxt = IMAPBox(
                    host=host, username=username, use_ssl=False, password='password',
                )

            with self.assertRaises(MailBox.Error) as exc_mngr:
                with ctxt:
                    pass

        self.assertEqual(
            _(
                'Error while retrieving emails on "{host}" for the user "{user}" '
                '[original error: {error}]'
            ).format(host=host, user=username, error=error_msg),
            str(exc_mngr.exception),
        )

    def test_IMAP_error02(self):
        "Error with some messages."
        msg_id1 = b'12'
        msg_id2 = b'25'

        msg2 = EmailMessage()
        msg2['Subject'] = 'I want a hammerhead'
        msg2['From'] = 'spike@bebop.spc'
        msg2['To'] = 'ed@spacemotor.mrs'

        msg_as_str2 = msg2.as_string()
        email_ids = []
        email_messages = []

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
            with IMAPBox(host='host', use_ssl=False,
                         username='username', password='password',
                         ) as box:
                for email_id in box:
                    email_ids.append(email_id)

                    with box.fetch_email(email_id) as email_message:
                        email_messages.append(email_message)

        imap_instance.store.assert_called_once_with(msg_id2, '+FLAGS', r'\Deleted')
        imap_instance.logout.assert_called_once()

        self.assertListEqual([msg_id1, msg_id2], email_ids)

        self.assertEqual(2, len(email_messages))
        self.assertIsNone(email_messages[0])

        retr_msg = email_messages[1]
        self.assertIsInstance(retr_msg, EmailMessage)
        self.assertEqual(msg2['Subject'], retr_msg['Subject'])
