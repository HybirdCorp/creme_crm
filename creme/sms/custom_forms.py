# -*- coding: utf-8 -*-

from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme import sms
from creme.creme_core.gui.custom_form import CustomFormDescriptor

Campaign = sms.get_smscampaign_model()
MessageTemplate = sms.get_messagetemplate_model()
MessagingList = sms.get_messaginglist_model()

CAMPAIGN_CREATION_CFORM = CustomFormDescriptor(
    id='sms-campaign_creation',
    model=Campaign,
    verbose_name=pgettext_lazy('sms', 'Creation form for campaign'),
)
CAMPAIGN_EDITION_CFORM = CustomFormDescriptor(
    id='sms-campaign_edition',
    model=Campaign,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=pgettext_lazy('sms', 'Edition form for campaign'),
    excluded_fields=('lists',),
)
TEMPLATE_CREATION_CFORM = CustomFormDescriptor(
    id='sms-template_creation',
    model=MessageTemplate,
    verbose_name=pgettext_lazy('emails', 'Creation form for template'),
)
TEMPLATE_EDITION_CFORM = CustomFormDescriptor(
    id='sms-template_edition',
    model=MessageTemplate,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=pgettext_lazy('emails', 'Edition form for template'),
)
MESSAGINGLIST_CREATION_CFORM = CustomFormDescriptor(
    id='sms-messaging_list_creation',
    model=MessagingList,
    verbose_name=_('Creation form for messaging list'),
)
MESSAGINGLIST_EDITION_CFORM = CustomFormDescriptor(
    id='sms-messaging_list_edition',
    model=MessagingList,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for messaging list'),
)

del Campaign
del MessageTemplate
del MessagingList
