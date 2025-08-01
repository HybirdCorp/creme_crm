################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator
from email.mime.image import MIMEImage
from email.utils import make_msgid, parseaddr
from os.path import basename, join
from random import choice
from re import compile as re_compile
from string import ascii_letters, digits
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.mail import EmailMessage, SafeMIMEMultipart, SafeMIMEText
from django.template.loader import get_template
from django.utils.timezone import now

from creme.documents.models import AbstractDocument

if TYPE_CHECKING:
    from creme.emails.models import EmailSignature

logger = logging.getLogger(__name__)
ALLOWED_CHARS = ascii_letters + digits


def generate_id():
    from .models.mail import ID_LENGTH
    return ''.join(choice(ALLOWED_CHARS) for i in range(ID_LENGTH))


def get_domain(email_address):
    _display_name, email = parseaddr(email_address)

    try:
        _email_user, host = email.rsplit('@', 1)
    except ValueError:
        return ''

    return host


_IMG_PATTERN = re_compile(
    r'<img.*src[\s]*[=]{1,1}["\']{1,1}(?P<img_src>[\d\w:/?\=.]*)["\']{1,1}'
)


class ImageFromHTMLError(Exception):
    def __init__(self, filename, *args, **kwargs):
        super().__init__(f'Can not use the image : {filename}')
        self._filename = filename

    @property
    def filename(self):
        return self._filename


# NB: not <class SignatureImage(MIMEImage):> because it would interact badly
#     with the template system (__getitem__ etc...)
class SignatureImage:
    class Error(Exception):
        pass

    def __init__(self, image_entity: AbstractDocument, domain: str):
        self.entity = image_entity
        self.domain = domain

        self.content_id = self._build_content_id()

        try:
            with image_entity.filedata.open() as image_file:
                mime_image = self._build_mime_image(image_file)
        except OSError as e:
            raise self.Error(f'Error during image reading [original:error: {e}]') from e

        self.mime = mime_image

    def __str__(self):
        return (
            f'SignatureImage('
            f'image_entity={self.entity},'
            f'sender_address="{self.domain}"'
            f')[content_id=>{self.content_id}]'
        )

    def _build_mime_image(self, image_file):
        mime_image = MIMEImage(image_file.read())
        mime_image.add_header('Content-ID', f'<{self.content_id}>')
        mime_image.add_header(
            'Content-Disposition', 'inline', filename=basename(image_file.name),
        )

        return mime_image

    def _build_content_id(self):
        # TODO use make_msgid()?
        return f'img_{self.entity.id}@{self.domain}'


class SignatureRenderer:
    text_template_name = 'emails/signature/content.txt'
    html_template_name = 'emails/signature/content.html'
    html_preview_template_name = 'emails/signature/preview.html'

    image_cls = SignatureImage

    def __init__(self, signature, domain: str):
        self._signature = signature
        self._images = images = []

        image_cls = self.image_cls
        for image_entity in signature.images.all():
            try:
                img = image_cls(image_entity=image_entity, domain=domain)
            except image_cls.Error as e:
                logger.error('Cannot create image: %s', e)
            else:
                images.append(img)

    @property
    def images(self) -> Iterator[SignatureImage]:
        yield from self._images

    def get_context(self) -> dict:
        return {
            'signature': self._signature,
            'images': self._images,
        }

    def render_text(self) -> str:
        return get_template(self.text_template_name).render(self.get_context())

    def render_html(self) -> str:
        return get_template(self.html_template_name).render(self.get_context())

    def render_html_preview(self) -> str:
        return get_template(self.html_preview_template_name).render(self.get_context())


class EMailSender:
    signature_render_cls = SignatureRenderer

    # TODO: keywords only
    def __init__(self, body: str, body_html: str,
                 signature: EmailSignature | None = None,
                 attachments: Iterable[AbstractDocument] = (),
                 *, sender_address: str,
                 ):
        """
        @raise ImageFromHTMLError.
        @raise ValueError When the domain cannot be extracted from 'sender_address'.
        """
        self._domain = domain = get_domain(sender_address)
        if not domain:
            raise ValueError(
                f'The domain of this address cannot be extracted: "{sender_address}"'
                if sender_address else 'Empty sender address'
            )

        self._body = body
        self._body_html = body_html
        self._attachments = [*attachments]
        self._signature_renderer = None

        if signature:
            self._signature_renderer = renderer = self.signature_render_cls(
                signature=signature, domain=domain,
            )
            self._body      += renderer.render_text()
            self._body_html += renderer.render_html()

    def get_subject(self, mail):
        raise NotImplementedError

    def _process_bodies(self, mail):
        return self._body, self._body_html

    def send(self, mail, connection=None):
        """Send the email & update its status.
        @param mail: Object with a class inheriting <emails.models.mail._Email>.
        @return True means 'OK mail was sent successfully'.
        """
        ok = False

        if mail.status == mail.Status.SENT:
            logger.error('Mail already sent to the recipient')
        else:
            body, body_html = self._process_bodies(mail)

            # In order to improve the render of inlined images inline (on some
            # mail clients, they can be not displayed & added as attachment instead)
            # we group the HTML parts & images in "multipart/related" part.
            # - msg - multipart/mixed
            #    - related_part - multipart/related
            #        - alt_part - multipart/alternative
            #            - text_part - text/plain
            #            - html_part - text/html
            #        - inline images mime parts - image/png etc...
            #    - attachments parts - application/pdf ...
            msg = EmailMessage(
                subject=self.get_subject(mail),
                body='',
                from_email=mail.sender,
                to=[mail.recipient],
                connection=connection,
                headers={
                    'Message-ID': make_msgid(idstring=str(mail.pk), domain=self._domain),
                },
            )

            related_part = SafeMIMEMultipart(_subtype='related', type='multipart/alternative')

            alt_part = SafeMIMEMultipart(_subtype='alternative')
            alt_part.attach(SafeMIMEText(body, _subtype='plain', _charset='utf-8'))
            alt_part.attach(SafeMIMEText(body_html, _subtype='html', _charset='utf-8'))
            related_part.attach(alt_part)

            if self._signature_renderer:
                for image in self._signature_renderer.images:
                    related_part.attach(image.mime)

            msg.attach(related_part)

            MEDIA_ROOT = settings.MEDIA_ROOT
            for attachment in self._attachments:
                msg.attach_file(join(MEDIA_ROOT, attachment.filedata.name))

            try:
                msg.send()
            except Exception:
                logger.exception('Sending: error during sending mail.')
                mail.status = mail.Status.SENDING_ERROR
            else:
                mail.status = mail.Status.SENT
                mail.sending_date = now()
                ok = True

            mail.save()

        return ok
