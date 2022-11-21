from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme import emails
from creme.creme_core.gui.custom_form import (
    CustomFormDefault,
    CustomFormDescriptor,
)
from creme.emails.forms.template import EmailTemplateBaseCustomForm

Campaign = emails.get_emailcampaign_model()
EmailTemplate = emails.get_emailtemplate_model()
MailingList = emails.get_mailinglist_model()


# ------------------------------------------------------------------------------
class EmailCampaignCreationFormDefault(CustomFormDefault):
    main_fields = ['user', 'name', 'mailing_lists']


class EmailCampaignEditionFormDefault(CustomFormDefault):
    main_fields = ['user', 'name']


CAMPAIGN_CREATION_CFORM = CustomFormDescriptor(
    id='emails-campaign_creation',
    model=Campaign,
    verbose_name=pgettext_lazy('emails', 'Creation form for campaign'),
    default=EmailCampaignCreationFormDefault,
)
CAMPAIGN_EDITION_CFORM = CustomFormDescriptor(
    id='emails-campaign_edition',
    model=Campaign,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=pgettext_lazy('emails', 'Edition form for campaign'),
    excluded_fields=('mailing_lists',),
    default=EmailCampaignEditionFormDefault,
)


# ------------------------------------------------------------------------------
class EmailTemplateFormDefault(CustomFormDefault):
    main_fields = [
        'user', 'name', 'subject', 'body', 'body_html', 'signature', 'attachments',
    ]


TEMPLATE_CREATION_CFORM = CustomFormDescriptor(
    id='emails-template_creation',
    model=EmailTemplate,
    verbose_name=pgettext_lazy('emails', 'Creation form for template'),
    base_form_class=EmailTemplateBaseCustomForm,
    default=EmailTemplateFormDefault,
)
TEMPLATE_EDITION_CFORM = CustomFormDescriptor(
    id='emails-template_edition',
    model=EmailTemplate,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=pgettext_lazy('emails', 'Edition form for template'),
    base_form_class=EmailTemplateBaseCustomForm,
    default=EmailTemplateFormDefault,
)


# ------------------------------------------------------------------------------
class MailingListFormDefault(CustomFormDefault):
    main_fields = ['user', 'name']


MAILINGLIST_CREATION_CFORM = CustomFormDescriptor(
    id='emails-mailing_list_creation',
    model=MailingList,
    verbose_name=_('Creation form for mailing list'),
    default=MailingListFormDefault,
)
MAILINGLIST_EDITION_CFORM = CustomFormDescriptor(
    id='emails-mailing_list_edition',
    model=MailingList,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for mailing list'),
    default=MailingListFormDefault,
)

del Campaign
del EmailTemplate
del MailingList
