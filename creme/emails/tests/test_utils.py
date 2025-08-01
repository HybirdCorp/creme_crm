from email.mime.image import MIMEImage

from django.core import mail as django_mail
from django.utils.html import escape

from creme.documents.tests.base import DocumentsTestCaseMixin

from ..models import EmailSignature
from ..utils import EMailSender, SignatureImage, SignatureRenderer, get_domain
from .base import EntityEmail, _EmailsTestCase


class UtilsTestCase(DocumentsTestCaseMixin, _EmailsTestCase):
    class TestEMailSender(EMailSender):
        subject = 'Test'

        def get_subject(self, mail):
            return self.subject

    def test_get_domain(self):
        self.assertEqual('bebop.mrs', get_domain('jet.black@bebop.mrs'))
        self.assertEqual('bigshot.jp', get_domain('faye.valentine@bigshot.jp'))

        self.assertEqual('bigshot.jp', get_domain('Faye <faye.valentine@bigshot.jp>'))
        self.assertEqual('bigshot.jp', get_domain('<faye.valentine@bigshot.jp>'))

        self.assertEqual('', get_domain(''))
        self.assertEqual('', get_domain('faye'))
        self.assertEqual('', get_domain('Faye <faye.valentine>'))
        self.assertEqual('', get_domain('Faye <>'))
        self.assertEqual('', get_domain('Faye <'))

    def test_signature_image(self):
        user = self.login_as_root_and_get()
        img = self._create_image(user=user)
        domain = 'test.org'

        with self.assertNoException():
            sig_img = SignatureImage(image_entity=img, domain=domain)

        self.assertEqual(img,    sig_img.entity)
        self.assertEqual(domain, sig_img.domain)
        self.assertEqual(f'img_{img.id}@{domain}', sig_img.content_id)

        mime_img = sig_img.mime
        self.assertIsInstance(mime_img, MIMEImage)
        self.assertEqual('image/png', mime_img.get_content_type())

        with self.assertNoException():
            header_content_id = mime_img['Content-ID']
        self.assertEqual(f'<img_{img.id}@{domain}>', header_content_id)

        with self.assertNoException():
            content_disp = mime_img['Content-Disposition']
        self.assertRegex(content_disp, r'inline; filename="creme_22(.*).png"')

    def test_signature_renderer(self):
        "With images."
        user = self.login_as_root_and_get()

        create_img = self._create_image
        img1 = create_img(user=user, title='My image#1', ident=1)
        img2 = create_img(user=user, title='My image#2', ident=2)

        signature = EmailSignature.objects.create(
            user=user, name='Funny signature', body='I love you... <b>not</b>',
        )
        signature.images.set([img1, img2])

        domain = 'test.com'
        renderer = SignatureRenderer(signature=signature, domain=domain)
        self.assertEqual(f'\n\n--\n{signature.body}', renderer.render_text())
        self.assertHTMLEqual(
            f'<div class="creme-emails-signature" id="signature-{signature.id}">'
            f'<p><br>--<br>{escape(signature.body)}</p>'
            f'<br/><img src="cid:img_{img1.id}@{domain}" />'
            f'<br/><img src="cid:img_{img2.id}@{domain}" />'
            f'</div>',
            renderer.render_html(),
        )
        self.assertHTMLEqual(
            f'<div class="creme-emails-signature" id="signature-{signature.id}">'
            f'<p><br>--<br>{escape(signature.body)}</p>'
            f'<br/>'
            f'<img src="{img1.get_download_absolute_url()}" '
            f'title="{img1.title}" alt="{img1.title}" />'
            f'<br/>'
            f'<img src="{img2.get_download_absolute_url()}" '
            f'title="{img2.title}" alt="{img2.title}" />'
            f'</div>',
            renderer.render_html_preview(),
        )

        rend_images = [*renderer.images]
        self.assertEqual(2, len(rend_images))

        rend_image1 = rend_images[0]
        self.assertIsInstance(rend_image1.mime, MIMEImage)
        self.assertEqual(img1, rend_image1.entity)

    def test_sender01(self):
        user = self.login_as_root_and_get()
        self.assertFalse(django_mail.outbox)

        sender = 'm.kusanagi@section9.jp'
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
        e_sender = MySender(body, body_html, sender_address=sender)
        mail = EntityEmail(user=user, sender=sender, recipient='bato@section9.jp')

        e_sender.send(mail)

        messages = django_mail.outbox
        self.assertEqual(len(messages), 1)

        message = messages[0]
        self.assertEqual(MySender.subject, message.subject)
        self.assertEqual(mail.sender,      message.from_email)
        self.assertEqual([mail.recipient], message.recipients())
        self.assertBodiesEqual(message, body=body, body_html=body_html)
        self.assertEqual(1, len(message.attachments))

    def test_sender02(self):
        "Signature (with images)."
        user = self.login_as_root_and_get()

        create_img = self._create_image
        img1 = create_img(user=user, title='My image#1', ident=1)
        img2 = create_img(user=user, title='My image#2', ident=2)

        signature = EmailSignature.objects.create(
            user=user, name='Funny signature', body='I love you... <b>not</b>',
        )
        signature.images.set([img1, img2])

        body = 'Want to meet you'
        body_html = '<p>Want to meet you</p>'

        MySender = self.TestEMailSender
        sender = 'm.kusanagi@section9.jp'
        e_sender = MySender(body, body_html, signature=signature, sender_address=sender)
        mail = EntityEmail(user=user, sender=sender, recipient='bato@section9.jp')

        e_sender.send(mail)
        message = self.get_alone_element(django_mail.outbox)

        self.assertEqual(MySender.subject, message.subject)
        self.assertEqual(mail.sender, message.from_email)
        self.assertBodiesEqual(
            message,
            body=f'{body}\n\n--\n{signature.body}',
            body_html=(
                f'{body_html}'
                f'<div class="creme-emails-signature" id="signature-{signature.id}">'
                f'<p><br>--<br>{escape(signature.body)}</p>'
                f'<br/><img src="cid:img_{img1.id}@section9.jp" />'
                f'<br/><img src="cid:img_{img2.id}@section9.jp" />'
                f'</div>'
            ),
            signature_images_types=['image/png'] * 2,
        )
        self.assertEqual(1, len(message.attachments))

    def test_sender__errors(self):
        with self.assertRaises(ValueError) as cm1:
            self.TestEMailSender(body='Hi', body_html='<h1>Hi<h/1>', sender_address='')
        self.assertEqual('Empty sender address', str(cm1.exception))

        with self.assertRaises(ValueError) as cm2:
            self.TestEMailSender(body='Hi', body_html='<h1>Hi<h/1>', sender_address='faye')
        self.assertEqual(
            'The domain of this address cannot be extracted: "faye"',
            str(cm2.exception),
        )

    # TODO: test_get_images_from_html03() -> 'attachments' parameter
