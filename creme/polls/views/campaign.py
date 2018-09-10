# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2018  Hybird
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

import warnings

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views import generic

from .. import get_pollcampaign_model
from ..constants import DEFAULT_HFILTER_PCAMPAIGN
from ..forms.campaign import PollCampaignForm


PollCampaign = get_pollcampaign_model()

# Function views --------------------------------------------------------------


def abstract_add_pcampaign(request, form=PollCampaignForm,
                           submit_label=PollCampaign.save_label,
                          ):
    warnings.warn('polls.views.campaign.abstract_add_pcampaign() is deprecated ; '
                  'use the class-based view PollCampaignCreation instead.',
                  DeprecationWarning
                 )
    return generic.add_entity(request, form,
                              extra_template_dict={'submit_label': submit_label},
                             )


def abstract_edit_pcampaign(request, campaign_id, form=PollCampaignForm):
    warnings.warn('polls.views.campaign.abstract_edit_pcampaign() is deprecated ; '
                  'use the class-based view PollCampaignEdition instead.',
                  DeprecationWarning
                 )
    return generic.edit_entity(request, campaign_id, PollCampaign, form)


def abstract_view_pcampaign(request, campaign_id,
                            template='polls/view_campaign.html',
                           ):
    warnings.warn('polls.views.campaign.abstract_view_pcampaign() is deprecated ; '
                  'use the class-based view PollCampaignDetail instead.',
                  DeprecationWarning
                 )
    return generic.view_entity(request, campaign_id, PollCampaign, template=template)


@login_required
@permission_required(('polls', cperm(PollCampaign)))
def add(request):
    warnings.warn('polls.views.campaign.add() is deprecated.', DeprecationWarning)
    return abstract_add_pcampaign(request)


@login_required
@permission_required('polls')
def edit(request, campaign_id):
    warnings.warn('polls.views.campaign.edit() is deprecated.', DeprecationWarning)
    return abstract_edit_pcampaign(request, campaign_id)


@login_required
@permission_required('polls')
def detailview(request, campaign_id):
    warnings.warn('polls.views.campaign.detailview() is deprecated.', DeprecationWarning)
    return abstract_view_pcampaign(request, campaign_id)


@login_required
@permission_required('polls')
def listview(request):
    return generic.list_view(request, PollCampaign, hf_pk=DEFAULT_HFILTER_PCAMPAIGN)


# Class-based views  ----------------------------------------------------------

class PollCampaignCreation(generic.add.EntityCreation):
    model = PollCampaign
    form_class = PollCampaignForm


class PollCampaignDetail(generic.detailview.EntityDetail):
    model = PollCampaign
    template_name = 'polls/view_campaign.html'
    pk_url_kwarg = 'campaign_id'


class PollCampaignEdition(generic.edit.EntityEdition):
    model = PollCampaign
    form_class = PollCampaignForm
    pk_url_kwarg = 'campaign_id'
