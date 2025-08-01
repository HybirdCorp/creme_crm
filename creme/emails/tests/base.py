from email.mime.image import MIMEImage
from functools import partial
from unittest import skipIf

from django.urls import reverse

from creme import documents, persons
from creme.creme_core.tests.base import CremeTestCase

from .. import (
    emailcampaign_model_is_custom,
    emailtemplate_model_is_custom,
    entityemail_model_is_custom,
    get_emailcampaign_model,
    get_emailtemplate_model,
    get_entityemail_model,
    get_mailinglist_model,
    mailinglist_model_is_custom,
)

skip_emailcampaign_tests = emailcampaign_model_is_custom()
skip_emailtemplate_tests = emailtemplate_model_is_custom()
skip_entityemail_tests   = entityemail_model_is_custom()
skip_mailinglist_tests   = mailinglist_model_is_custom()

EmailCampaign = get_emailcampaign_model()
EntityEmail   = get_entityemail_model()
MailingList   = get_mailinglist_model()
EmailTemplate = get_emailtemplate_model()

Folder   = documents.get_folder_model()
Document = documents.get_document_model()

Contact      = persons.get_contact_model()
Organisation = persons.get_organisation_model()


def skipIfCustomEmailCampaign(test_func):
    return skipIf(skip_emailcampaign_tests, 'Custom EmailCampaign model in use')(test_func)


def skipIfCustomEmailTemplate(test_func):
    return skipIf(skip_emailtemplate_tests, 'Custom EmailTemplate model in use')(test_func)


def skipIfCustomEntityEmail(test_func):
    return skipIf(skip_entityemail_tests, 'Custom EntityEmail model in use')(test_func)


def skipIfCustomMailingList(test_func):
    return skipIf(skip_mailinglist_tests, 'Custom MailingList model in use')(test_func)


class _EmailsTestCase(CremeTestCase):
    def login_as_emails_user(self, *, allowed_apps=(), **kwargs):
        return super().login_as_standard(
            allowed_apps=['emails', *allowed_apps],
            **kwargs
        )

    def login_as_emails_admin(self, *, allowed_apps=(), admin_4_apps=(), **kwargs):
        return super().login_as_standard(
            allowed_apps=['emails', *allowed_apps],
            admin_4_apps=['emails', *admin_4_apps],
            **kwargs
        )

    def assertBodiesEqual(self, message, body, body_html, signature_images_types=()):
        bodies_attachment = message.attachments[0]
        self.assertTrue(bodies_attachment.is_multipart())

        alt_attachment = bodies_attachment.get_payload(0)
        body_payload = alt_attachment.get_payload(0)
        self.assertEqual('text/plain', body_payload.get_content_type())
        self.assertEqual(body,         body_payload.get_payload())

        body_html_payload = alt_attachment.get_payload(1)
        self.assertEqual('text/html', body_html_payload.get_content_type())
        self.assertHTMLEqual(body_html, body_html_payload.get_payload())

        for i, img_type in enumerate(signature_images_types):
            img = bodies_attachment.get_payload(1 + i)
            self.assertIsInstance(img, MIMEImage)
            self.assertEqual(img_type, img.get_content_type())

        with self.assertRaises(IndexError):
            alt_attachment.get_payload(2 + len(signature_images_types))

    @staticmethod
    def _build_create_entitymail_url(entity):
        return reverse('emails__create_email', args=(entity.id,))

    def _create_email(self,
                      user,
                      status=EntityEmail.Status.NOT_SENT,
                      recipient='vincent.law@immigrates.rmd',
                      subject='Under arrest',
                      body='Freeze!',
                      body_html='<p>Freeze!</p>',
                      signature=None,
                      ):
        return EntityEmail.objects.create(
            user=user,
            sender=user.linked_contact.email,
            recipient=recipient,
            subject=subject,
            body=body,
            status=status,
            body_html=body_html,
            signature=signature,
        )

    def _create_emails(self, user):
        if persons.contact_model_is_custom():
            self.fail(
                'Cannot use _EmailsTestCase._create_emails() with custom Contact model.'
            )

        if persons.organisation_model_is_custom():
            self.fail(
                'Cannot use _EmailsTestCase._create_emails() with custom Organisation model.'
            )

        create_c = partial(Contact.objects.create, user=user)
        contacts = [
            create_c(
                first_name='Vincent',  last_name='Law', email='vincent.law@immigrates.rmd',
            ),
            create_c(
                first_name='Daedalus', last_name='??',  email='daedalus@research.rmd',
            ),
        ]

        create_o = partial(Organisation.objects.create, user=user)
        orgas = [
            create_o(name='Venus gate', email='contact@venusgate.jp'),
            create_o(name='Nerv',       email='contact@nerv.jp'),
        ]

        url = self._build_create_entitymail_url(contacts[0])
        self.assertGET200(url)

        response = self.client.post(
            url,
            data={
                'user': user.id,
                'sender': 're-l.mayer@rpd.rmd',

                'c_recipients': self.formfield_value_multi_creator_entity(
                    contacts[0],
                    contacts[1],
                ),
                'o_recipients': self.formfield_value_multi_creator_entity(
                    orgas[0],
                    orgas[1],
                ),
                'subject': 'Under arrest',
                'body': 'Freeze',
                'body_html': '<p>Freeze !</p>',
            },
        )
        self.assertNoFormError(response)

        emails = EntityEmail.objects.all()
        self.assertEqual(4, len(emails))

        return emails
