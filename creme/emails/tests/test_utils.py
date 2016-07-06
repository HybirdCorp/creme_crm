# -*- coding: utf-8 -*-

try:
    from email.mime.image import MIMEImage
    from os.path import join, exists, basename

    from django.conf import settings
    from django.core import mail as django_mail

    from creme.media_managers.tests import create_image
    from creme.media_managers.models import Image

    from .base import _EmailsTestCase, EntityEmail
    from ..models import EmailSignature  # EntityEmail
    from ..utils import get_mime_image, get_images_from_html, EMailSender
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class UtilsTestCase(_EmailsTestCase):
    def setUp(self):
        self.images = []

    # TODO: remove when documents & images have been merged -> use the CremeTestCase.tearDown cleaning.
    def tearDown(self):
        for img in self.images:
            img.delete()

    class TestEMailSender(EMailSender):
        subject = 'Test'

        def get_subject(self, mail):
            return self.subject

    # TODO: factorise (copied from MediaManagersTestCase, then simplified) (see setUp/tearDown too)
    def _create_image(self, name='My image', filename='creme_22.png'):
        path = join(settings.CREME_ROOT, 'static', 'chantilly', 'images', 'creme_22.png')
        self.assertTrue(exists(path))
        image_file = open(path, 'rb')

        response = self.client.post('/media_managers/image/add', follow=True,
                                    data={'user':  self.user.pk,
                                          'name':  name,
                                          'image': image_file,
                                         }
                                   )
        self.assertNoFormError(response)

        with self.assertNoException():
            image = Image.objects.get(name=name)

        self.images.append(image)

        return  image

    def test_get_mime_image01(self):
        "File does not exist"
        user = self.login()
        img = create_image(user)

        img = self.refresh(img) # NamedTemporaryFile.file seems annoying (not a true file)...

        with self.assertNoException():
            imime = get_mime_image(img)

        self.assertIsNone(imime)

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

        self.assertEqual('<img_%s>' % img.id, content_id)

        with self.assertNoException():
            content_disp = imime['Content-Disposition']

        # self.assertIn('inline', content_disp)
        # self.assertIn('creme_22.png', content_disp)
        self.assertRegexpMatches(content_disp, r'inline; filename="(\d+)_creme_22_(\d+)_(\d+).png"')

    def test_get_images_from_html(self):
        self.login()
        img1 = self._create_image(name='My image#1', filename='creme_22.png')
        img2 = self._create_image(name='My image#2', filename='add_22.png')

        url1 = img1.get_image_url()
        url2 = img2.get_image_url()

        html = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html>
    <head>
        <title>My title</title>
    </head>
    <body>
        <p>blabla</p>
        <p><img title="My image#1" src="%s" alt="Image esc#1" width="159" height="130" /></p>
        <p>other blabla</p>
        <p><img title="My image#2" src="http://external.image.org/12345.png" alt="Image esc#2" width="123" height="148" /></p>
        <p><img title="My image#2" src="%s" alt="Image esc#2" width="123" height="148" /></p>
    </body>
</html>""" % (url1, url2)

        images = get_images_from_html(html)
        self.assertIsInstance(images, dict)
        self.assertEqual(2, len(images))

        self.assertEqual((img1, url1), images.get(basename(img1.image.path)))
        self.assertEqual((img2, url2), images.get(basename(img2.image.path)))

    def test_sender01(self):
        user = self.login()
        self.assertFalse(django_mail.outbox)

        html_fmt = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html>
    <head>
        <title>Important</title>
    </head>
    <body>
        <p>Want to meet you</p>
        <img title="My image#1" src="%s" alt="" width="22" height="22" />
    </body>
</html>"""

        img = self._create_image()
        body = 'Want to meet you'
        body_html = html_fmt % img.get_image_url()

        MySender = self.TestEMailSender
        e_sender = MySender(body, body_html)
        mail = EntityEmail(user=user, sender='m.kusanagi@section9.jp')

        e_sender.send(mail)

        messages = django_mail.outbox
        self.assertEqual(len(messages), 1)

        message = messages[0]
        self.assertEqual(MySender.subject, message.subject)
        self.assertEqual(body,             message.body)
        self.assertEqual(mail.sender,      message.from_email)
        self.assertEqual([(html_fmt % ('cid:img_%s' % img.id), 'text/html')],
                         message.alternatives
                        )

        attachments = message.attachments
        self.assertEqual(1, len(attachments))
        self.assertIsInstance(attachments[0], MIMEImage)

    def test_sender02(self):
        "Signature (with images)"
        user = self.login()

        img1 = self._create_image(name='My image#1', filename='creme_22.png')
        img2 = self._create_image(name='My image#2', filename='add_22.png')

        signature = EmailSignature.objects.create(user=user,
                                                  name='Funny signature',
                                                  body='I love you... not',
                                                 )
        signature.images = [img1, img2]

        body = 'Want to meet you'
        body_html = '<p>Want to meet you</p>'

        MySender = self.TestEMailSender
        e_sender = MySender(body, body_html, signature=signature)
        mail = EntityEmail(user=user, sender='m.kusanagi@section9.jp')

        e_sender.send(mail)

        messages = django_mail.outbox
        self.assertEqual(len(messages), 1)

        message = messages[0]
        self.assertEqual(MySender.subject, message.subject)
        self.assertEqual(u'%s\n--\n%s' % (body, signature.body), message.body)
        self.assertEqual(mail.sender, message.from_email)

        alternatives = message.alternatives
        self.assertEqual(1, len(alternatives))

        alternative = alternatives[0]
        self.assertEqual('text/html', alternative[1])
        self.assertEqual(body_html + '\n--\n' + signature.body +
                            '<img src="cid:img_%s" /><br/><img src="cid:img_%s" /><br/>' % (
                                    img1.id, img2.id
                                ),
                         alternative[0]
                        )

        attachments = message.attachments
        self.assertEqual(2, len(attachments))
        self.assertIsInstance(attachments[0], MIMEImage)
        self.assertIsInstance(attachments[1], MIMEImage)

    # TODO: test_get_images_from_html03() -> 'attachments' parameter
