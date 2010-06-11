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

from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType

from creme_core.entities_access.functions_for_permissions import get_view_or_die, add_view_or_die, edit_object_or_die, delete_object_or_die
from creme_core.views.generic import add_entity, edit_entity, view_entity_with_template, list_view, inner_popup

from sms.models import SMSCampaign
from sms.forms.campaign import CampaignCreateForm, CampaignEditForm, CampaignAddSendListForm
from sms.blocks import sendlists_block


@login_required
@get_view_or_die('sms')
@add_view_or_die(ContentType.objects.get_for_model(SMSCampaign), None, 'sms')
def add(request):
    return add_entity(request, CampaignCreateForm)

def edit(request, id):
    return edit_entity(request, id, SMSCampaign, CampaignEditForm, 'sms')

# TODO : perhaps more reliable to forbid delete for campaigns with sendings.
@login_required
def delete(request, id): 
    campaign = get_object_or_404(SMSCampaign, pk=id).get_real_entity()

    die_status = delete_object_or_die(request, campaign)
    if die_status:
        return die_status

    callback_url = campaign.get_lv_absolute_url()

    campaign.delete()
    
    return HttpResponseRedirect(callback_url)

@login_required
@get_view_or_die('sms')
def detailview(request, id):
    return view_entity_with_template(request, id, SMSCampaign,
                                     '/sms/campaign',
                                     'sms/view_campaign.html')

@login_required
@get_view_or_die('sms')
def listview(request):
    return list_view(request, SMSCampaign, extra_dict={'add_url': '/sms/campaign/add'})

@login_required
@get_view_or_die('sms')
def add_sendlist(request, id):
    campaign = get_object_or_404(SMSCampaign, pk=id)

    die_status = edit_object_or_die(request, campaign)
    if die_status:
        return die_status

    if request.POST:
        ml_add_form = CampaignAddSendListForm(campaign, request.POST)

        if ml_add_form.is_valid():
            ml_add_form.save()
    else:
        ml_add_form = CampaignAddSendListForm(campaign=campaign)

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {
                        'form':   ml_add_form,
                        'title': 'Nouvelles listes de diffusion pour <%s>' % campaign,
                       },
                       is_valid=ml_add_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))

@login_required
@get_view_or_die('sms')
def delete_sendlist(request, campaign_id, id):
    campaign = get_object_or_404(SMSCampaign, pk=campaign_id)

    die_status = edit_object_or_die(request, campaign)
    if die_status:
        return die_status

    campaign.sendlists.remove(id)

    return HttpResponseRedirect(campaign.get_absolute_url())

@login_required
def reload_block_sendlist(request, id):
    return sendlists_block.detailview_ajax(request, id)
