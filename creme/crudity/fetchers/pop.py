# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

import email
import logging
import poplib
import re
from datetime import datetime
from typing import Iterable, List, Tuple

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile, UploadedFile

from creme.creme_core.utils import safe_unicode

from .base import CrudityFetcher

logger = logging.getLogger(__name__)


class PopEmail:
    def __init__(self,
                 # TODO: '*'
                 body: str = '',
                 body_html: str = '',
                 senders: Iterable[str] = (),
                 tos: Iterable[str] = (),
                 ccs: Iterable[str] = (),
                 subject: str = '',
                 dates: Iterable[datetime] = (),
                 attachments: Iterable[Tuple[str, UploadedFile]] = (),
                 ):
        self.subject   = subject
        self.body      = body
        self.body_html = body_html

        self.senders: List[str] = [*senders]
        self.tos: List[str]     = [*tos]
        self.ccs: List[str]     = [*ccs]

        self.dates: List[datetime] = [*dates]

        self.attachments: List[Tuple[str, UploadedFile]] = [*attachments]


class PopFetcher(CrudityFetcher):
    def fetch(self, delete=True):  # TODO: args read from configuration instead ?
        client = None
        emails = []

        CREME_GET_EMAIL_SERVER = settings.CREME_GET_EMAIL_SERVER
        CREME_GET_EMAIL_PORT   = settings.CREME_GET_EMAIL_PORT

        try:
            if settings.CREME_GET_EMAIL_SSL:
                client = poplib.POP3_SSL(
                    CREME_GET_EMAIL_SERVER, CREME_GET_EMAIL_PORT,
                    settings.CREME_GET_EMAIL_SSL_KEYFILE,
                    settings.CREME_GET_EMAIL_SSL_CERTFILE,
                )
            else:
                client = poplib.POP3(CREME_GET_EMAIL_SERVER, CREME_GET_EMAIL_PORT)

            client.user(settings.CREME_GET_EMAIL_USERNAME)
            client.pass_(settings.CREME_GET_EMAIL_PASSWORD)

            client.stat()  # TODO: useful ?
            response, messages, total_size = client.list()
        except Exception:  # TODO: Define better exception
            logger.exception("PopFetcher.fetch: POP connection error")

            if client is not None:
                client.quit()

            return []

        getaddresses = email.utils.getaddresses
        parsedate    = email.utils.parsedate

        for msg_info in messages:
            attachments = []
            message_number, message_size = msg_info.split()
            message_number = int(message_number)
            r, raw_message_lines, message_size = client.retr(message_number)

            out_str = b'\n'.join(raw_message_lines)
            out_str = re.sub(b'\r(?!=\n)', b'\r\n', out_str)

            email_message = email.message_from_bytes(out_str)
            get_all = email_message.get_all

            to_emails   = [addr for name, addr in getaddresses(get_all('to', []))]
            from_emails = [addr for name, addr in getaddresses(get_all('from', []))]
            cc_emails   = [addr for name, addr in getaddresses(get_all('cc', []))]

            subject = ''.join(
                s.decode(enc) if enc is not None else safe_unicode(s)
                for s, enc in email.header.decode_header(email_message.get('subject', []))
            )

            dates = [datetime(*parsedate(d)[:-3]) for d in get_all('date', []) if d is not None]

            body_html = ''
            body = ''
            # CONTENT HTML / PLAIN
            if email_message.is_multipart():
                for part in email_message.walk():
                    payload = part.get_payload(decode=True)

                    mct = part.get_content_maintype()
                    cst = part.get_content_subtype()

                    if mct == 'multipart':
                        continue

                    filename = part.get_filename()

                    if mct != 'text' or (mct == 'text' and filename is not None):
                        attachments.append((
                            filename,
                            SimpleUploadedFile(
                                filename, payload, content_type=part.get_content_type(),
                            ),
                        ))

                    else:
                        content = payload
                        if cst == 'html':
                            body_html = safe_unicode(content)
                        elif cst == 'plain':
                            body = safe_unicode(content)
                        # else:  TODO ??
            else:
                cst = email_message.get_content_subtype()
                content = email_message.get_payload(decode=True)
                if cst == 'plain':
                    body = safe_unicode(content)
                elif cst == 'html':
                    body_html = body = safe_unicode(content)

            emails.append(PopEmail(
                body=body,
                body_html=body_html,
                senders=from_emails,
                tos=to_emails,
                ccs=cc_emails,
                subject=subject,
                dates=dates,
                attachments=attachments,
            ))

            if delete:
                # We delete the mail from the server when treated
                # TODO: delete only when we are sure it has been saved (clean() method ?)
                client.dele(message_number)

        client.quit()

        return emails
