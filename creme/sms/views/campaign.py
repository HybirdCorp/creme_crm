# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from django.http import HttpResponse  # HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views.generic import (add_entity, add_to_entity,
        edit_entity, view_entity, list_view)

from .. import get_smscampaign_model
from ..constants import DEFAULT_HFILTER_SMSCAMPAIGN
from ..forms.campaign import CampaignCreateForm, CampaignEditForm, CampaignAddListForm


SMSCampaign = get_smscampaign_model()


def abstract_add_smscampaign(request, form=CampaignCreateForm,
                             submit_label=SMSCampaign.save_label,
                            ):
    return add_entity(request, form,
                      extra_template_dict={'submit_label': submit_label},
                     )


def abstract_edit_smscampaign(request, campaign_id, form=CampaignEditForm):
    return edit_entity(request, campaign_id, SMSCampaign, form)


def abstract_view_smscampaign(request, campaign_id,
                              template='sms/view_campaign.html',
                             ):
    return view_entity(request, campaign_id, SMSCampaign, template=template)


@login_required
# @permission_required(('sms', 'sms.add_smscampaign'))
@permission_required(('sms', cperm(SMSCampaign)))
def add(request):
    return abstract_add_smscampaign(request)


@login_required
@permission_required('sms')
def edit(request, campaign_id):
    return abstract_edit_smscampaign(request, campaign_id)


# TODO : perhaps more reliable to forbid delete for campaigns with sendings.
# @login_required
# @permission_required('sms')
# def delete(request, id):
#     campaign = get_object_or_404(SMSCampaign, pk=id)
#     request.user.has_perm_to_delete_or_die(campaign)
#
#     callback_url = campaign.get_lv_absolute_url()
#
#     campaign.delete()
#
#     return HttpResponseRedirect(callback_url)


@login_required
@permission_required('sms')
def detailview(request, campaign_id):
    return abstract_view_smscampaign(request, campaign_id)


@login_required
@permission_required('sms')
def listview(request):
    return list_view(request, SMSCampaign, hf_pk=DEFAULT_HFILTER_SMSCAMPAIGN)


@login_required
@permission_required('sms')
def add_messaging_list(request, campaign_id):
    return add_to_entity(request, campaign_id, CampaignAddListForm,
                         ugettext(u'New messaging lists for «%s»'),
                         entity_class=SMSCampaign,
                         submit_label=_(u'Link the messaging lists'),
                         template='creme_core/generics/blockform/link_popup.html',
                        )


@login_required
@permission_required('sms')
def delete_messaging_list(request, campaign_id):
    campaign = get_object_or_404(SMSCampaign, pk=campaign_id)
    request.user.has_perm_to_change_or_die(campaign)

    campaign.lists.remove(request.POST.get('id'))

    if request.is_ajax():
        # return HttpResponse(content_type='text/javascript')
        return HttpResponse()

    return redirect(campaign)
