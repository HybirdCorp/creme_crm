# -*- coding: utf-8 -*-

from email.mime.image import MIMEImage

from django.core import mail as django_mail

from creme.documents.tests.base import _DocumentsTestCase

from ..models import EmailSignature
from ..utils import EMailSender, get_mime_image
from .base import EntityEmail, _EmailsTestCase


class UtilsTestCase(_EmailsTestCase, _DocumentsTestCase):
    class TestEMailSender(EMailSender):
        subject = 'Test'

        def get_subject(self, mail):
            return self.subject

    def test_get_mime_image02(self):
        "PNG"
        self.login()
        img = self._create_image()

        with self.assertNoException():
            imime = get_mime_image(img)

        self.assertIsInstance(imime, MIMEImage)
        self.assertEqual('image/png', imime.get_content_type())

        with self.assertNoException():
            content_id = imime['Content-ID']

        self.assertEqual(f'<img_{img.id}>', content_id)

        with self.assertNoException():
            content_disp = imime['Content-Disposition']

        self.assertRegex(content_disp, r'inline; filename="creme_22(.*).png"')

    def test_sender01(self):
        user = self.login()
        self.assertFalse(django_mail.outbox)

        body = 'Want to meet you'
        body_html = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html>
    <head>
        <title>Important</title>
    </head>
    <body>
        <p>Want to meet you</p>
    </body>
</html>"""  # NOQA

        MySender = self.TestEMailSender
        e_sender = MySender(body, body_html)
        mail = EntityEmail(
            user=user, sender='m.kusanagi@section9.jp', recipient='bato@section9.jp',
        )

        e_sender.send(mail)

        messages = django_mail.outbox
        self.assertEqual(len(messages), 1)

        message = messages[0]
        self.assertEqual(MySender.subject, message.subject)
        self.assertEqual(body,             message.body)
        self.assertEqual(mail.sender,      message.from_email)
        self.assertEqual([mail.recipient], message.recipients())
        self.assertEqual([(body_html, 'text/html')], message.alternatives)

        self.assertFalse(message.attachments)

    def test_sender02(self):
        "Signature (with images)."
        user = self.login()

        create_img = self._create_image
        img1 = create_img(title='My image#1', ident=1)
        img2 = create_img(title='My image#2', ident=2)

        signature = EmailSignature.objects.create(
            user=user, name='Funny signature', body='I love you... not',
        )
        signature.images.set([img1, img2])

        body = 'Want to meet you'
        body_html = '<p>Want to meet you</p>'

        MySender = self.TestEMailSender
        e_sender = MySender(body, body_html, signature=signature)
        mail = EntityEmail(
            user=user, sender='m.kusanagi@section9.jp', recipient='bato@section9.jp',
        )

        e_sender.send(mail)

        messages = django_mail.outbox
        self.assertEqual(len(messages), 1)

        message = messages[0]
        self.assertEqual(MySender.subject, message.subject)
        self.assertEqual(f'{body}\n--\n{signature.body}', message.body)
        self.assertEqual(mail.sender, message.from_email)

        alternatives = message.alternatives
        self.assertEqual(1, len(alternatives))

        alternative = alternatives[0]
        self.assertEqual('text/html', alternative[1])
        self.assertEqual(
            body_html
            + '\n--\n'
            + signature.body
            + f'<img src="cid:img_{img1.id}" /><br/><img src="cid:img_{img2.id}" /><br/>',
            alternative[0]
        )

        attachments = message.attachments
        self.assertEqual(2, len(attachments))
        self.assertIsInstance(attachments[0], MIMEImage)
        self.assertIsInstance(attachments[1], MIMEImage)

    # TODO: test_get_images_from_html03() -> 'attachments' parameter
