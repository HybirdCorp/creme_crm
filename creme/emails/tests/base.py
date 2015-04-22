# -*- coding: utf-8 -*-

skip_emailcampaign_tests = False
skip_emailtemplate_tests = False
skip_entityemail_tests   = False
skip_mailinglist_tests   = False

try:
    from unittest import skipIf

    from creme.creme_core.models import SettingValue
    from creme.creme_core.tests.base import CremeTestCase

    from creme.persons import get_contact_model, get_organisation_model
    #from creme.persons.models import Contact, Organisation

    from .. import (get_entityemail_model, emailcampaign_model_is_custom,
            emailtemplate_model_is_custom, entityemail_model_is_custom,
            mailinglist_model_is_custom)
    from ..constants import (REL_SUB_MAIL_RECEIVED, REL_SUB_MAIL_SENDED,
            REL_SUB_RELATED_TO, SETTING_EMAILCAMPAIGN_SENDER)
    #from ..models import EntityEmail

    skip_emailcampaign_tests = emailcampaign_model_is_custom()
    skip_emailtemplate_tests = emailtemplate_model_is_custom()
    skip_entityemail_tests   = entityemail_model_is_custom()
    skip_mailinglist_tests   = mailinglist_model_is_custom()
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('EmailsTestCase',)


def skipIfCustomEmailCampaign(test_func):
    return skipIf(skip_emailcampaign_tests, 'Custom EmailCampaign model in use')(test_func)

def skipIfCustomEmailTemplate(test_func):
    return skipIf(skip_emailtemplate_tests, 'Custom EmailTemplate model in use')(test_func)

def skipIfCustomEntityEmail(test_func):
    return skipIf(skip_entityemail_tests, 'Custom EntityEmail model in use')(test_func)

def skipIfCustomMailingList(test_func):
    return skipIf(skip_mailinglist_tests, 'Custom MailingList model in use')(test_func)


class _EmailsTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        CremeTestCase.setUpClass()
        cls.populate('creme_core', 'emails')


class EmailsTestCase(_EmailsTestCase):
    def test_populate(self):
        EntityEmail = get_entityemail_model()
        Contact = get_contact_model()
        Organisation = get_organisation_model()
        
        self.get_relationtype_or_fail(REL_SUB_MAIL_RECEIVED, [EntityEmail], [Organisation, Contact])
        self.get_relationtype_or_fail(REL_SUB_MAIL_SENDED,   [EntityEmail], [Organisation, Contact])
        self.get_relationtype_or_fail(REL_SUB_RELATED_TO,    [EntityEmail])

        self.assertEqual(1, SettingValue.objects.filter(key_id=SETTING_EMAILCAMPAIGN_SENDER).count())

    def test_portal(self):
        self.login()
        self.assertGET200('/emails/')
