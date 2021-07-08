# -*- coding: utf-8 -*-

from functools import partial
from unittest import skipIf

from django.urls import reverse

from creme import documents, persons
from creme.creme_core.tests.base import CremeTestCase

# from ..constants import MAIL_STATUS_NOTSENT
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
    def login(self, allowed_apps=('emails',), *args, **kwargs):
        return super().login(allowed_apps=allowed_apps, *args, **kwargs)

    @staticmethod
    def _build_create_entitymail_url(entity):
        return reverse('emails__create_email', args=(entity.id,))

    # def _create_email(self, status=MAIL_STATUS_NOTSENT, body_html='', signature=None):
    def _create_email(self, status=EntityEmail.Status.NOT_SENT, body_html='', signature=None):
        user = self.user
        return EntityEmail.objects.create(
            user=user,
            sender=user.linked_contact.email,
            recipient='vincent.law@immigrates.rmd',
            subject='Under arrest',
            body='Freeze !',
            status=status,
            body_html=body_html,
            signature=signature,
        )

    def _create_emails(self):
        if persons.contact_model_is_custom():
            self.fail(
                'Cannot use _EmailsTestCase._create_emails() with custom Contact model.'
            )

        if persons.organisation_model_is_custom():
            self.fail(
                'Cannot use _EmailsTestCase._create_emails() with custom Organisation model.'
            )

        user = self.user

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
