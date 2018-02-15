# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from datetime import datetime
import email
import poplib
import logging
import re

from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings

from creme.creme_core.utils import safe_unicode

from .base import CrudityFetcher


logger = logging.getLogger(__name__)


class PopEmail(object):
    def __init__(self, body=u'', body_html=u'', senders=(), tos=(), ccs=(), subject='', dates=(), attachments=()):
        self.body        = body
        self.body_html   = body_html
        self.senders     = senders
        self.tos         = tos
        self.ccs         = ccs
        self.subject     = subject
        self.dates       = dates
        self.attachments = attachments


class PopFetcher(CrudityFetcher):
    def fetch(self, delete=True):  # TODO: args read from configuration instead ?
        client = None
        emails = []

        CREME_GET_EMAIL_SERVER = settings.CREME_GET_EMAIL_SERVER
        CREME_GET_EMAIL_PORT   = settings.CREME_GET_EMAIL_PORT

        try:
            if settings.CREME_GET_EMAIL_SSL:
                client = poplib.POP3_SSL(CREME_GET_EMAIL_SERVER, CREME_GET_EMAIL_PORT,
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

            message_number, message_size = msg_info.split(' ')
            r, raw_message_lines, message_size = client.retr(message_number)

            out_str = '\n'.join(raw_message_lines)
            out_str = re.sub(r'\r(?!=\n)', '\r\n', out_str)

            email_message = email.message_from_string(out_str)
            get_all = email_message.get_all

            to_emails   = [addr for name, addr in getaddresses(get_all('to', []))]
            from_emails = [addr for name, addr in getaddresses(get_all('from', []))]
            cc_emails   = [addr for name, addr in getaddresses(get_all('cc', []))]

            subject = ''.join(s.decode(enc) if enc is not None else s
                                for s, enc in email.Header.decode_header(email_message.get('subject', []))
                             )

            dates = [datetime(*parsedate(d)[:-3]) for d in get_all('date', []) if d is not None]

            body_html = u''
            body = u''
            # CONTENT HTML / PLAIN
            if email_message.is_multipart():
                for part in email_message.walk():
                    encodings = set(part.get_charsets())
                    encodings.discard(None)

                    payload = part.get_payload(decode=True)

                    mct = part.get_content_maintype()
                    cst = part.get_content_subtype()

                    if mct == 'multipart':
                        continue

                    filename = part.get_filename()

                    if mct != 'text' or (mct == 'text' and filename is not None):
                        attachments.append((filename, SimpleUploadedFile(filename, payload,
                                                                         content_type=part.get_content_type(),
                                                                        )
                                           )
                                          )

                    else:
                        content = safe_unicode(payload, encodings)
                        if cst == 'html':
                            body_html = content
                        elif cst == 'plain':
                            body = content
                        # else:  TODO ??
            else:
                encodings = set(email_message.get_charsets())
                encodings.discard(None)

                cst = email_message.get_content_subtype()
                content = safe_unicode(email_message.get_payload(decode=True), encodings)
                if cst == 'plain':
                    body = content
                elif cst == 'html':
                    body_html = body = content

            emails.append(PopEmail(body, body_html, from_emails, to_emails, cc_emails, subject, dates, attachments))

            if delete:
                # We delete the mail from the server when treated
                client.dele(message_number)

        client.quit()

        return emails

pop_fetcher = PopFetcher()  # DEPRECATED
