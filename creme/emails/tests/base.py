# -*- coding: utf-8 -*-

skip_emailcampaign_tests = False
skip_emailtemplate_tests = False
skip_entityemail_tests   = False
skip_mailinglist_tests   = False

try:
    from functools import partial
    from unittest import skipIf

    from django.urls import reverse

    from creme.creme_core.tests.base import CremeTestCase

    from creme.documents import get_document_model, get_folder_model

    from creme.persons import get_contact_model, get_organisation_model
    from creme.persons.tests.base import skipIfCustomContact, skipIfCustomOrganisation

    from .. import (emailcampaign_model_is_custom, emailtemplate_model_is_custom,
            entityemail_model_is_custom, mailinglist_model_is_custom,
            get_emailcampaign_model, get_entityemail_model,
            get_emailtemplate_model, get_mailinglist_model)

    skip_emailcampaign_tests = emailcampaign_model_is_custom()
    skip_emailtemplate_tests = emailtemplate_model_is_custom()
    skip_entityemail_tests   = entityemail_model_is_custom()
    skip_mailinglist_tests   = mailinglist_model_is_custom()

    EmailCampaign = get_emailcampaign_model()
    EntityEmail   = get_entityemail_model()
    MailingList   = get_mailinglist_model()
    EmailTemplate = get_emailtemplate_model()
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


Folder   = get_folder_model()
Document = get_document_model()

Contact       = get_contact_model()
Organisation  = get_organisation_model()


def skipIfCustomEmailCampaign(test_func):
    return skipIf(skip_emailcampaign_tests, 'Custom EmailCampaign model in use')(test_func)


def skipIfCustomEmailTemplate(test_func):
    return skipIf(skip_emailtemplate_tests, 'Custom EmailTemplate model in use')(test_func)


def skipIfCustomEntityEmail(test_func):
    return skipIf(skip_entityemail_tests, 'Custom EntityEmail model in use')(test_func)


def skipIfCustomMailingList(test_func):
    return skipIf(skip_mailinglist_tests, 'Custom MailingList model in use')(test_func)


class _EmailsTestCase(CremeTestCase):
    def _build_create_entitymail_url(self, entity):
        return reverse('emails__create_email', args=(entity.id,))

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def _create_emails(self):
        user = self.user

        create_c = partial(Contact.objects.create, user=user)
        contacts = [create_c(first_name='Vincent',  last_name='Law', email='vincent.law@immigrates.rmd'),
                    create_c(first_name='Daedalus', last_name='??',  email='daedalus@research.rmd'),
                   ]

        create_o = partial(Organisation.objects.create, user=user)
        orgas = [create_o(name='Venus gate', email='contact@venusgate.jp'),
                 create_o(name='Nerv',       email='contact@nerv.jp'),
                ]

        url = self._build_create_entitymail_url(contacts[0])
        self.assertGET200(url)

        response = self.client.post(url, data={'user':         user.id,
                                               'sender':       're-l.mayer@rpd.rmd',
                                               'c_recipients': '[%d,%d]' % (contacts[0].id, contacts[1].id),
                                               'o_recipients': '[%d,%d]' % (orgas[0].id, orgas[1].id),
                                               'subject':      'Under arrest',
                                               'body':         'Freeze',
                                               'body_html':    '<p>Freeze !</p>',
                                              }
                                   )
        self.assertNoFormError(response)

        emails = EntityEmail.objects.all()
        self.assertEqual(4, len(emails))

        return emails
