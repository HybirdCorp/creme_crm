# -*- coding: utf-8 -*-

skip_emailcampaign_tests = False
skip_emailtemplate_tests = False
skip_entityemail_tests   = False
skip_mailinglist_tests   = False

try:
    from unittest import skipIf

    from creme.creme_core.tests.base import CremeTestCase

    from .. import (emailcampaign_model_is_custom, emailtemplate_model_is_custom,
            entityemail_model_is_custom, mailinglist_model_is_custom)

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
