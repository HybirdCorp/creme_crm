# -*- coding: utf-8 -*-

from unittest import skipIf

from creme import persons, sms

skip_smscampaign_tests     = sms.smscampaign_model_is_custom()
skip_messaginglist_tests   = sms.messaginglist_model_is_custom()
skip_messagetemplate_tests = sms.messagetemplate_model_is_custom()

SMSCampaign     = sms.get_smscampaign_model()
MessageTemplate = sms.get_messagetemplate_model()
MessagingList   = sms.get_messaginglist_model()

Contact = persons.get_contact_model()


def skipIfCustomSMSCampaign(test_func):
    return skipIf(skip_smscampaign_tests, 'Custom SMSCampaign model in use')(test_func)


def skipIfCustomMessagingList(test_func):
    return skipIf(skip_messaginglist_tests, 'Custom MessagingList model in use')(test_func)


def skipIfCustomMessageTemplate(test_func):
    return skipIf(skip_messagetemplate_tests, 'Custom MessageTemplate model in use')(test_func)
