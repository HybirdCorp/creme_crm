# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2014  Hybird
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

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views.generic import view_entity, add_entity, edit_entity, list_view

from ..forms.campaign import PollCampaignForm
from ..models import PollCampaign


@login_required
@permission_required('polls')
@permission_required('polls.add_pollcampaign')
def add(request):
    return add_entity(request, PollCampaignForm,
                      extra_template_dict={'submit_label': _('Save the campaign of polls')},
                     )

@login_required
@permission_required('polls')
def edit(request, campaign_id):
    return edit_entity(request, campaign_id, PollCampaign, PollCampaignForm)

@login_required
@permission_required('polls')
def detailview(request, campaign_id):
    return view_entity(request, campaign_id, PollCampaign,
                       '/polls/campaign', 'polls/view_campaign.html',
                      )

@login_required
@permission_required('polls')
def listview(request):
    return list_view(request, PollCampaign,
                     extra_dict={'add_url': '/polls/campaign/add'},
                    )
