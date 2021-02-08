# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

import logging
from email.mime.image import MIMEImage
from os.path import basename, join
from random import choice
from re import compile as re_compile
from string import ascii_letters, digits

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.timezone import now

# from .constants import MAIL_STATUS_SENDINGERROR, MAIL_STATUS_SENT

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


_MIME_IMG_CACHE = '_mime_image_cache'


def get_mime_image(image_entity):
    try:
        mime_image = getattr(image_entity, _MIME_IMG_CACHE)
    except AttributeError:
        try:
            with image_entity.filedata.open() as image_file:
                mime_image = MIMEImage(image_file.read())
                mime_image.add_header(
                    'Content-ID', f'<img_{image_entity.id}>',
                )
                mime_image.add_header(
                    'Content-Disposition', 'inline', filename=basename(image_file.name),
                )
        except IOError as e:
            logger.error('Exception when reading image : %s', e)
            mime_image = None

        setattr(image_entity, _MIME_IMG_CACHE, mime_image)

    return mime_image


class EMailSender:
    def __init__(self, body, body_html, signature=None, attachments=()):
        "@throws ImageFromHTMLError"
        mime_images = []

        if signature:
            signature_body = '\n--\n' + signature.body

            body += signature_body
            body_html += signature_body

            for image_entity in signature.images.all():
                mime_image = get_mime_image(image_entity)

                if mime_image is None:
                    logger.error(
                        'Error during reading attached image in signature: %s',
                        image_entity,
                    )
                else:
                    mime_images.append(mime_image)
                    body_html += f'<img src="cid:img_{image_entity.id}" /><br/>'

        self._body      = body
        self._body_html = body_html

        self._attachments = attachments
        self._mime_images = mime_images

    def get_subject(self, mail):
        raise NotImplementedError

    def _process_bodies(self, mail):
        return self._body, self._body_html

    def send(self, mail, connection=None):
        """
        @param mail: Object with a class inheriting emails.models.mail._Email
        @return True means <OK mail was sent>
        """
        ok = False

        # if mail.status == MAIL_STATUS_SENT:
        if mail.status == mail.Status.SENT:
            logger.error('Mail already sent to the recipient')
        else:
            body, body_html = self._process_bodies(mail)

            msg = EmailMultiAlternatives(
                self.get_subject(mail), body, mail.sender, [mail.recipient],
                connection=connection,
            )
            msg.attach_alternative(body_html, 'text/html')

            for image in self._mime_images:
                msg.attach(image)

            MEDIA_ROOT = settings.MEDIA_ROOT
            for attachment in self._attachments:
                msg.attach_file(join(MEDIA_ROOT, attachment.filedata.name))

            try:
                msg.send()
            except Exception:
                logger.exception('Sending: error during sending mail.')
                # mail.status = MAIL_STATUS_SENDINGERROR
                mail.status = mail.Status.SENDING_ERROR
            else:
                # mail.status = MAIL_STATUS_SENT
                mail.status = mail.Status.SENT
                mail.sending_date = now()
                ok = True

            mail.save()

        return ok
