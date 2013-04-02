# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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
from email.mime.image import MIMEImage
import logging
from os.path import basename, exists, join
from random import choice
from re import compile as re_compile, findall as re_findall
from string import ascii_letters, digits

from django.core.mail import EmailMultiAlternatives
from django.conf import settings

from creme.media_managers.models import Image

from .constants import MAIL_STATUS_SENT, MAIL_STATUS_SENDINGERROR


logger = logging.getLogger(__name__)
ALLOWED_CHARS = ascii_letters + digits

def generate_id():
    from .models.mail import ID_LENGTH
    return ''.join(choice(ALLOWED_CHARS) for i in xrange(ID_LENGTH))


_IMG_PATTERN = re_compile(r'<img.*src[\s]*[=]{1,1}["\']{1,1}(?P<img_src>[\d\w:/?\=.]*)["\']{1,1}')

class ImageFromHTMLError(Exception):
    def __init__(self, filename, *args, **kwargs):
        super(Exception, self).__init__('Can not use the image : %s' % filename)
        self._filename = filename

    @property
    def filename(self):
        return self._filename


def get_images_from_html(html):
    """Extract refernce to Image entities in an HTML string:

        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
        <html>
            <head>
                <title>My title</title>
            </head>
            <body>
                <p>blabla</p>
                <p><img title="My image" src="http://127.0.0.1:8000/site_media/upload/images/12_imagename.jpg" alt="Image esc" width="159" height="130" /></p>
            </body>
        </html>

    => {'12_imagename.jpg': (<Image object (id=12)>), 'http://127.0.0.1:8000/site_media/upload/images/12_imagename.jpg'}

    @return Dict where keys are filenames, and values are tuples (Image object, source)
            Image object can be None if the Image entity was not found.
    """
    MEDIA_ROOT = settings.MEDIA_ROOT
    images_info = {} #key=Image.id  Value=(source, basefilename)

    for source in re_findall(_IMG_PATTERN, html):
        filename = basename(source)

        if not exists(join(MEDIA_ROOT, "upload", "images", filename)):
            raise ImageFromHTMLError(filename)

        try:
            images_info[int(filename.split('_', 1)[0])] = (source, filename)
        except ValueError:
            raise ImageFromHTMLError(filename)

    images_map = dict((image.id, image) for image in Image.objects.filter(pk__in=images_info.iterkeys()))

    return dict((filename, (images_map.get(image_id), source))
                    for image_id, (source, filename) in images_info.iteritems()
               )



_MIME_IMG_CACHE = '_mime_image_cache'

def get_mime_image(image_entity):
    try:
        mime_image = getattr(image_entity, _MIME_IMG_CACHE)
    except AttributeError:
        try:
            image_file = image_entity.image.file
            image_file.open() #TODO: 'with' ??
            mime_image = MIMEImage(image_file.read())
            mime_image.add_header('Content-ID','<img_%s>' % image_entity.id)
            mime_image.add_header('Content-Disposition', 'inline', filename=basename(image_file.name))
            image_file.close()
        except IOError as e:
            logger.error('Exception when reading image : %s', e)
            mime_image = None

        setattr(image_entity, _MIME_IMG_CACHE, mime_image)

    return mime_image


class EMailSender(object):
    def __init__(self, body, body_html, signature=None, attachments=()):
        "@throws ImageFromHTMLError"
        mime_images = []

        #Replacing image sources with embbeded images
        for filename, (image_entity, src) in get_images_from_html(body_html).iteritems(): #can throws ImageFromHTMLError
            if image_entity is None:
                logger.error('Image with filename <%s> do not exist any more.')
            else:
                mime_image = get_mime_image(image_entity)

                if mime_image is None:
                    logger.error('Error during reading attached image: %s', filename)
                else:
                    mime_images.append(mime_image)
                    body_html = body_html.replace(src, 'cid:img_%s' % image_entity.id)

        if signature:
            signature_body = '\n--\n' + signature.body

            body += signature_body
            body_html += signature_body

            for image_entity in signature.images.all():
                mime_image = get_mime_image(image_entity)

                if mime_image is None:
                    logger.error('Error during reading attached image in signature: %s', image_entity)
                else:
                    mime_images.append(mime_image)
                    body_html += '<img src="cid:img_%s" /><br/>' % image_entity.id

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
        @param mail Object with a class inherting emails.models.mail._Email
        @return True means: OK mail was sent
        """
        ok = False

        if mail.status == MAIL_STATUS_SENT:
            logger.error('Mail already sent to the recipient')
        else:
            body, body_html = self._process_bodies(mail)

            msg = EmailMultiAlternatives(self.get_subject(mail), body, mail.sender, [mail.recipient], connection=connection)
            msg.attach_alternative(body_html, "text/html")

            for image in self._mime_images:
                msg.attach(image)

            MEDIA_ROOT = settings.MEDIA_ROOT
            for attachment in self._attachments:
                msg.attach_file(join(MEDIA_ROOT, attachment.filedata.name))

            try:
                msg.send()
            except Exception:
                logger.exception('Sending: error during sending mail.')
                mail.status = MAIL_STATUS_SENDINGERROR
            else:
                mail.status = MAIL_STATUS_SENT
                mail.sending_date = datetime.now() #####??
                ok = True

            mail.save()

        return ok
