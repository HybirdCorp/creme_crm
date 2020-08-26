# -*- coding: utf-8 -*-

from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme import polls
from creme.creme_core.gui.custom_form import CustomFormDescriptor

PollCampaign = polls.get_pollcampaign_model()
PollForm = polls.get_pollform_model()

CAMPAIGN_CREATION_CFORM = CustomFormDescriptor(
    id='polls-campaign_creation',
    model=PollCampaign,
    verbose_name=pgettext_lazy('polls', 'Creation form for campaign'),
)
CAMPAIGN_EDITION_CFORM = CustomFormDescriptor(
    id='polls-campaign_edition',
    model=PollCampaign,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=pgettext_lazy('polls', 'Edition form for campaign'),
)
PFORM_CREATION_CFORM = CustomFormDescriptor(
    id='polls-pform_creation',
    model=PollForm,
    verbose_name=_('Creation form for poll-form'),
)
PFORM_EDITION_CFORM = CustomFormDescriptor(
    id='polls-pform_edition',
    model=PollForm,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for poll-form'),
)
# TODO: PollReply:
#   - what about replies multi creation ?
#   - edition

del PollCampaign
del PollForm
