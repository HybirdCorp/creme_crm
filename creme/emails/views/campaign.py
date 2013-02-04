# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required, permission_required

from creme_core.views.generic import add_entity, add_to_entity, edit_entity, view_entity, list_view
from creme_core.utils import get_from_POST_or_404

from emails.models import EmailCampaign
from emails.forms.campaign import CampaignCreateForm, CampaignEditForm, CampaignAddMLForm


@login_required
@permission_required('emails')
@permission_required('emails.add_emailcampaign')
def add(request):
    return add_entity(request, CampaignCreateForm)

@login_required
@permission_required('emails')
def edit(request, campaign_id):
    return edit_entity(request, campaign_id, EmailCampaign, CampaignEditForm)

@login_required
@permission_required('emails')
def detailview(request, campaign_id):
    return view_entity(request, campaign_id, EmailCampaign, '/emails/campaign', 'emails/view_campaign.html')

@login_required
@permission_required('emails')
def listview(request):
    return list_view(request, EmailCampaign, extra_dict={'add_url': '/emails/campaign/add'})

@login_required
@permission_required('emails')
def add_ml(request, campaign_id):
    return add_to_entity(request, campaign_id, CampaignAddMLForm,
                         _('New mailing lists for <%s>'), entity_class=EmailCampaign)

@login_required
@permission_required('emails')
def delete_ml(request, campaign_id):
    ml_id    = get_from_POST_or_404(request.POST, 'id')
    campaign = get_object_or_404(EmailCampaign, pk=campaign_id)

    campaign.can_change_or_die(request.user)

    campaign.mailing_lists.remove(ml_id)

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")

    return HttpResponseRedirect(campaign.get_absolute_url())
