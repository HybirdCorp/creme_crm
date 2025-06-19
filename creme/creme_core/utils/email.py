################################################################################
#
# Copyright (c) 2022-2025 Hybird
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
################################################################################

from __future__ import annotations

import imaplib
import logging
import poplib
import socket
from collections.abc import Iterator
from email import message_from_bytes, policy
from email.message import EmailMessage
from typing import Union

from django.utils.translation import gettext

logger = logging.getLogger(__name__)
EmailID = Union[int, bytes]


class MailBox:
    """Retrieve all the emails of a box (abstract base class)."""
    class Error(Exception):
        pass

    error_classes = (socket.error, )

    class _EmailFetcher:
        def __init__(self, box: MailBox, email_id: EmailID):
            self._box = box
            self._email_id = email_id
            self._retrieved = False

        def __enter__(self) -> EmailMessage | None:
            if self._box._client is None:
                raise RuntimeError(
                    'The manager returned by "fetch_mail" must be used within '
                    'the context of the MailBox.'
                )

            email_id = self._email_id
            if email_id is None:
                return None

            try:
                as_bytes = self._retrieve_email_as_bytes(email_id)
            except self._box.error_classes:
                # TODO: delete the message anyway?
                logger.exception('Email sync: retrieving the email "%s" failed.', email_id)

                return None

            self._retrieved = True

            return message_from_bytes(as_bytes, policy=policy.default)

        def __exit__(self, exc_type, exc_val, exc_tb):
            email_id = self._email_id

            if email_id is not None and self._retrieved and exc_type is None:
                # We delete the mail from the server when treated
                try:
                    self._delete_email(email_id)
                except self._box.error_classes:
                    logger.warning('Email sync: deleting the email "%s" failed.', email_id)

        def _retrieve_email_as_bytes(self, email_id: EmailID) -> bytes:
            raise NotImplementedError

        def _delete_email(self, email_id: EmailID) -> None:
            raise NotImplementedError

    def __init__(self, *,
                 host: str,
                 port: int | None = None,
                 use_ssl: bool,
                 username: str,
                 password: str,
                 ):
        self._host = host
        self._port = port
        self._use_ssl = use_ssl
        self._username = username
        self._password = password

        self._client = None
        self._email_ids = None
        self._client_cls = None

    def __enter__(self) -> MailBox:
        assert self._email_ids is None  # Only enter once
        assert self._client_cls is not None

        host = self._host
        username = self._username

        logger.info(
            'Email sync: connect to email server with host=%s, username="%s" ...',
            host, username,
        )

        # TODO: "timeout" parameter?
        client_kwargs = {'host': host}
        if self._port:
            client_kwargs['port'] = self._port

        try:
            self._client = self._client_cls(**client_kwargs)
            self._login()
        except self.error_classes as e:
            logger.exception('Error while logging to mail box')

            raise self.Error(
                gettext(
                    'Error while retrieving emails on "{host}" for the user "{user}" '
                    '[original error: {error}]'
                ).format(host=host, user=username, error=e)
            )

        return self

    def __exit__(self, exc_type, exc_value, tb):
        if self._client is not None:
            try:
                self._quit()
            except self.error_classes:
                logger.exception('Email sync: error at quit.')

            self._client = None

    def __iter__(self):
        assert self._email_ids is None  # Only iter once

        self._email_ids = email_ids = []
        try:
            email_ids.extend(self._retrieve_ids())
        except self.error_classes:
            logger.exception('Error while retrieving email IDs')

        yield from email_ids

    def _login(self) -> None:
        raise NotImplementedError

    def _retrieve_ids(self) -> Iterator[EmailID]:
        raise NotImplementedError

    def _quit(self) -> None:
        raise NotImplementedError

    def fetch_email(self, email_id: EmailID):
        return self._EmailFetcher(box=self, email_id=email_id)


class POPBox(MailBox):
    """Retrieve all the emails of a box with the protocol POP3."""
    error_classes = (*MailBox.error_classes, poplib.error_proto)

    class _EmailFetcher(MailBox._EmailFetcher):
        def _retrieve_email_as_bytes(self, email_id):
            _response, raw_email_lines, _msg_size = self._box._client.retr(email_id)

            return b'\n'.join(raw_email_lines)

        def _delete_email(self, email_id):
            self._box._client.dele(email_id)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._client_cls = poplib.POP3_SSL if self._use_ssl else poplib.POP3

    def _login(self):
        client = self._client
        client.user(self._username)
        client.pass_(self._password)

    def _retrieve_ids(self):
        _response, emails_info, _total_size = self._client.list()

        for email_info in emails_info:
            try:
                # NB: email_info == b'{msg_id} {msg_size}'
                email_id = int(email_info.split(b' ', 1)[0])
            except ValueError:
                logger.warning('Email sync: the email info "%s" was invalid', email_info)
                email_id = None

            yield email_id

    def _quit(self):
        self._client.quit()


class IMAPBox(MailBox):
    """Retrieve all the emails of a box with the protocol IMAP4."""
    error_classes = (*MailBox.error_classes, imaplib.IMAP4.error)

    class _EmailFetcher(MailBox._EmailFetcher):
        def _retrieve_email_as_bytes(self, email_id):
            # TODO: uid('fetch', email_id, "(BODY[HEADER])")
            # TODO: is it possible to not retrieve attachments
            #       (when we do not want them) ?
            _response, raw_email_data = self._box._client.fetch(email_id, '(RFC822)')

            return raw_email_data[0][1]

        def _delete_email(self, email_id):
            self._box._client.store(email_id, '+FLAGS', r'\Deleted')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._client_cls = imaplib.IMAP4_SSL if self._use_ssl else imaplib.IMAP4

    def _login(self):
        self._client.login(self._username, self._password)

    def _retrieve_ids(self):
        client = self._client

        # TODO: check if _response is 'OK or 'NO'?
        _response, count_info = client.select()  # Select the default mailbox 'Inbox'
        msg_count = int(count_info[0])
        logger.info('%s message(s) in the main mailbox', msg_count)

        if msg_count:
            # TODO: uid('search', None, 'ALL') ?
            # TODO: check if _response is 'OK or 'NO'?
            _response, messages_info = client.search(None, 'ALL')
            yield from messages_info[0].split()

    def _quit(self):
        client = self._client

        # TODO: only if some valid messages?
        # if email_ids: # TODO ?
        # client.select('Trash')  TODO?
        client.expunge()

        client.close()
        client.logout()
