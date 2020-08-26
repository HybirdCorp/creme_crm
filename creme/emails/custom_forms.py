# -*- coding: utf-8 -*-

from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme import emails
from creme.creme_core.gui.custom_form import CustomFormDescriptor
from creme.emails.forms.template import EmailTemplateBaseCustomForm

Campaign = emails.get_emailcampaign_model()
EmailTemplate = emails.get_emailtemplate_model()
MailingList = emails.get_mailinglist_model()

CAMPAIGN_CREATION_CFORM = CustomFormDescriptor(
    id='emails-campaign_creation',
    model=Campaign,
    verbose_name=pgettext_lazy('emails', 'Creation form for campaign'),
)
CAMPAIGN_EDITION_CFORM = CustomFormDescriptor(
    id='emails-campaign_edition',
    model=Campaign,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=pgettext_lazy('emails', 'Edition form for campaign'),
    excluded_fields=('mailing_lists',),
)
TEMPLATE_CREATION_CFORM = CustomFormDescriptor(
    id='emails-template_creation',
    model=EmailTemplate,
    verbose_name=pgettext_lazy('emails', 'Creation form for template'),
    base_form_class=EmailTemplateBaseCustomForm,
)
TEMPLATE_EDITION_CFORM = CustomFormDescriptor(
    id='emails-template_edition',
    model=EmailTemplate,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=pgettext_lazy('emails', 'Edition form for template'),
    base_form_class=EmailTemplateBaseCustomForm,
)
MAILINGLIST_CREATION_CFORM = CustomFormDescriptor(
    id='emails-mailing_list_creation',
    model=MailingList,
    verbose_name=_('Creation form for mailing list'),
)
MAILINGLIST_EDITION_CFORM = CustomFormDescriptor(
    id='emails-mailing_list_edition',
    model=MailingList,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for mailing list'),
)

del Campaign
del EmailTemplate
del MailingList
