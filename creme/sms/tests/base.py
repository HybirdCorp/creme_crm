# -*- coding: utf-8 -*-

skip_smscampaign_tests     = False
skip_messaginglist_tests   = False
skip_messagetemplate_tests = False

try:
    from unittest import skipIf

    from creme import sms

    skip_smscampaign_tests     = sms.smscampaign_model_is_custom()
    skip_messaginglist_tests   = sms.messaginglist_model_is_custom()
    skip_messagetemplate_tests = sms.messagetemplate_model_is_custom()

    SMSCampaign = sms.get_smscampaign_model()
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


def skipIfCustomSMSCampaign(test_func):
    return skipIf(skip_smscampaign_tests, 'Custom SMSCampaign model in use')(test_func)


def skipIfCustomMessagingList(test_func):
    return skipIf(skip_messaginglist_tests, 'Custom MessagingList model in use')(test_func)


def skipIfCustomMessageTemplate(test_func):
    return skipIf(skip_messagetemplate_tests, 'Custom MessageTemplate model in use')(test_func)
