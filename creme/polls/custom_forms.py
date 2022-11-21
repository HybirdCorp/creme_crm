from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme import polls
from creme.creme_core.gui.custom_form import (
    CustomFormDefault,
    CustomFormDescriptor,
)

# TODO: PollReply:
#   - what about replies multi creation ?
#   - edition
PollCampaign = polls.get_pollcampaign_model()
PollForm = polls.get_pollform_model()


# ------------------------------------------------------------------------------
class PollCampaignFormDefault(CustomFormDefault):
    main_fields = [
        'user',
        'name',
        'goal',
        'start',
        'due_date',
        'segment',
        'expected_count',
    ]


CAMPAIGN_CREATION_CFORM = CustomFormDescriptor(
    id='polls-campaign_creation',
    model=PollCampaign,
    verbose_name=pgettext_lazy('polls', 'Creation form for campaign'),
    default=PollCampaignFormDefault,
)
CAMPAIGN_EDITION_CFORM = CustomFormDescriptor(
    id='polls-campaign_edition',
    model=PollCampaign,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=pgettext_lazy('polls', 'Edition form for campaign'),
    default=PollCampaignFormDefault,
)


# ------------------------------------------------------------------------------
class PollFormFormDefault(CustomFormDefault):
    main_fields = ['user', 'name', 'type']


PFORM_CREATION_CFORM = CustomFormDescriptor(
    id='polls-pform_creation',
    model=PollForm,
    verbose_name=_('Creation form for poll-form'),
    default=PollFormFormDefault,
)
PFORM_EDITION_CFORM = CustomFormDescriptor(
    id='polls-pform_edition',
    model=PollForm,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for poll-form'),
    default=PollFormFormDefault,
)

del PollCampaign
del PollForm
