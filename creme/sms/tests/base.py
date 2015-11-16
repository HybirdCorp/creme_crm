# -*- coding: utf-8 -*-

skip_smscampaign_tests     = False
skip_messaginglist_tests   = False
skip_messagetemplate_tests = False

try:
    from unittest import skipIf

    from .. import (smscampaign_model_is_custom, messaginglist_model_is_custom,
            messagetemplate_model_is_custom, get_smscampaign_model)

    skip_smscampaign_tests     = smscampaign_model_is_custom()
    skip_messaginglist_tests   = messaginglist_model_is_custom()
    skip_messagetemplate_tests = messagetemplate_model_is_custom()

    SMSCampaign = get_smscampaign_model()
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


def skipIfCustomSMSCampaign(test_func):
    return skipIf(skip_smscampaign_tests, 'Custom SMSCampaign model in use')(test_func)


def skipIfCustomMessagingList(test_func):
    return skipIf(skip_messaginglist_tests, 'Custom MessagingList model in use')(test_func)


def skipIfCustomMessageTemplate(test_func):
    return skipIf(skip_messagetemplate_tests, 'Custom MessageTemplate model in use')(test_func)
