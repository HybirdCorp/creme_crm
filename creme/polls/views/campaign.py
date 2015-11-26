# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2015  Hybird
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

# from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views.generic import view_entity, add_entity, edit_entity, list_view

from .. import get_pollcampaign_model
from ..constants import DEFAULT_HFILTER_PCAMPAIGN
from ..forms.campaign import PollCampaignForm
#from ..models import PollCampaign


PollCampaign = get_pollcampaign_model()


def abstract_add_pcampaign(request, form=PollCampaignForm,
                           submit_label=_('Save the campaign of polls'),
                          ):
    return add_entity(request, form,
                      extra_template_dict={'submit_label': submit_label},
                     )


def abstract_edit_pcampaign(request, campaign_id, form=PollCampaignForm):
    return edit_entity(request, campaign_id, PollCampaign, form)


def abstract_view_pcampaign(request, campaign_id,
                            template='polls/view_campaign.html',
                           ):
    return view_entity(request, campaign_id, PollCampaign, template=template,
                       # path='/polls/campaign',
                      )


@login_required
# @permission_required(('polls', 'polls.add_pollcampaign'))
@permission_required(('polls', cperm(PollCampaign)))
def add(request):
    return abstract_add_pcampaign(request)


@login_required
@permission_required('polls')
def edit(request, campaign_id):
    return abstract_edit_pcampaign(request, campaign_id)


@login_required
@permission_required('polls')
def detailview(request, campaign_id):
    return abstract_view_pcampaign(request, campaign_id)


@login_required
@permission_required('polls')
def listview(request):
    return list_view(request, PollCampaign, hf_pk=DEFAULT_HFILTER_PCAMPAIGN,
                     # extra_dict={'add_url': '/polls/campaign/add'},
                     # extra_dict={'add_url': reverse('polls__create_campaign')},
                    )
