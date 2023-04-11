################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2023  Hybird
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
from dataclasses import dataclass
from email.mime.image import MIMEImage
from os.path import basename, join
from random import choice
from re import compile as re_compile
from string import ascii_letters, digits
from typing import Iterable, Iterator

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.utils.timezone import now

from creme.documents.models import AbstractDocument

logger = logging.getLogger(__name__)
ALLOWED_CHARS = ascii_letters + digits


def generate_id():
    from .models.mail import ID_LENGTH
    return ''.join(choice(ALLOWED_CHARS) for i in range(ID_LENGTH))


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


# _MIME_IMG_CACHE = '_mime_image_cache'
#
# def get_mime_image(image_entity):
#     try:
#         mime_image = getattr(image_entity, _MIME_IMG_CACHE)
#     except AttributeError:
#         try:
#             with image_entity.filedata.open() as image_file:
#                 mime_image = MIMEImage(image_file.read())
#                 mime_image.add_header(
#                     'Content-ID', f'<img_{image_entity.id}>',
#                 )
#                 mime_image.add_header(
#                     'Content-Disposition', 'inline', filename=basename(image_file.name),
#                 )
#         except OSError as e:
#             logger.error('Exception when reading image : %s', e)
#             mime_image = None
#
#         setattr(image_entity, _MIME_IMG_CACHE, mime_image)
#
#     return mime_image
def get_mime_image(image_entity: AbstractDocument) -> MIMEImage | None:
    mime_image = None

    try:
        with image_entity.filedata.open() as image_file:
            mime_image = MIMEImage(image_file.read())
            mime_image.add_header(
                'Content-ID', f'<img_{image_entity.id}>',
            )
            mime_image.add_header(
                'Content-Disposition', 'inline', filename=basename(image_file.name),
            )
    except OSError as e:
        logger.error('Exception when reading image: %s', e)

    return mime_image


class SignatureRenderer:
    text_template_name = 'emails/signature/content.txt'
    html_template_name = 'emails/signature/content.html'
    html_preview_template_name = 'emails/signature/preview.html'

    @dataclass
    class Image:
        entity: AbstractDocument
        mime: MIMEImage

    def __init__(self, signature):
        self._signature = signature
        self._images = images = []

        for image_entity in signature.images.all():
            mime_image = get_mime_image(image_entity)

            if mime_image is None:
                logger.error(
                    'Error during reading attached image in signature: %s',
                    image_entity,
                )
            else:
                images.append(self.Image(entity=image_entity, mime=mime_image))

    @property
    def images(self) -> Iterator[Image]:
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

    # def __init__(self, body: str, body_html: str, signature=None, attachments=()):
    #     mime_images = []
    #
    #     if signature:
    #         signature_body = f'\n--\n{signature.body}'
    #         body += signature_body
    #         body_html += signature_body
    #
    #         for image_entity in signature.images.all():
    #             mime_image = get_mime_image(image_entity)
    #
    #             if mime_image is None:
    #                 logger.error(
    #                     'Error during reading attached image in signature: %s',
    #                     image_entity,
    #                 )
    #             else:
    #                 mime_images.append(mime_image)
    #                 body_html += f'<img src="cid:img_{image_entity.id}" /><br/>'
    #
    #     self._body = body
    #     self._body_html = body_html
    #
    #     self._attachments = attachments
    #     self._mime_images = mime_images
    def __init__(self, body: str, body_html: str, signature=None,
                 attachments: Iterable[AbstractDocument] = (),
                 ):
        "@raise ImageFromHTMLError."
        self._body = body
        self._body_html = body_html
        self._attachments = [*attachments]
        self._signature_renderer = None

        if signature:
            self._signature_renderer = renderer = self.signature_render_cls(signature)
            self._body      += renderer.render_text()
            self._body_html += renderer.render_html()

    def get_subject(self, mail):
        raise NotImplementedError

    def _process_bodies(self, mail):
        return self._body, self._body_html

    def send(self, mail, connection=None):
        """Send the email & update its status.
        @param mail: Object with a class inheriting <emails.models.mail._Email>.
        @return True means 'OK mail was sent>'.
        """
        ok = False

        if mail.status == mail.Status.SENT:
            logger.error('Mail already sent to the recipient')
        else:
            body, body_html = self._process_bodies(mail)

            msg = EmailMultiAlternatives(
                self.get_subject(mail), body, mail.sender, [mail.recipient],
                connection=connection,
            )
            msg.attach_alternative(body_html, 'text/html')

            # for image in self._mime_images:
            #     msg.attach(image)
            if self._signature_renderer:
                for image in self._signature_renderer.images:
                    msg.attach(image.mime)

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
