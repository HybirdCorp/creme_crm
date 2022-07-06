################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2021  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from creme.creme_core.views import generic

from .. import custom_forms, get_pollcampaign_model
from ..constants import DEFAULT_HFILTER_PCAMPAIGN

PollCampaign = get_pollcampaign_model()


class PollCampaignCreation(generic.EntityCreation):
    model = PollCampaign
    form_class = custom_forms.CAMPAIGN_CREATION_CFORM


class PollCampaignDetail(generic.EntityDetail):
    model = PollCampaign
    template_name = 'polls/view_campaign.html'
    pk_url_kwarg = 'campaign_id'


class PollCampaignEdition(generic.EntityEdition):
    model = PollCampaign
    form_class = custom_forms.CAMPAIGN_EDITION_CFORM
    pk_url_kwarg = 'campaign_id'


class PollCampaignsList(generic.EntitiesList):
    model = PollCampaign
    default_headerfilter_id = DEFAULT_HFILTER_PCAMPAIGN
