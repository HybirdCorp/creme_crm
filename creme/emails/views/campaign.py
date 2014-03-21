# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views.generic import (add_entity, add_to_entity,
        edit_entity, view_entity, list_view)
from creme.creme_core.utils import get_from_POST_or_404

from ..models import EmailCampaign
from ..forms.campaign import CampaignCreateForm, CampaignEditForm, CampaignAddMLForm


@login_required
@permission_required('emails')
@permission_required('emails.add_emailcampaign')
def add(request):
    return add_entity(request, CampaignCreateForm,
                      extra_template_dict={'submit_label': _('Save the emailing campaign')},
                     )

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
                         ugettext('New mailing lists for <%s>'),
                         entity_class=EmailCampaign,
                        )

@login_required
@permission_required('emails')
def delete_ml(request, campaign_id):
    ml_id    = get_from_POST_or_404(request.POST, 'id')
    campaign = get_object_or_404(EmailCampaign, pk=campaign_id)

    request.user.has_perm_to_change_or_die(campaign)

    campaign.mailing_lists.remove(ml_id)

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")

    return redirect(campaign)
