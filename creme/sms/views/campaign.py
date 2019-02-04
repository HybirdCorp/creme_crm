# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

# import warnings

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext_lazy as _

# from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views import generic

from .. import get_smscampaign_model
from ..constants import DEFAULT_HFILTER_SMSCAMPAIGN
from ..forms import campaign as camp_forms


SMSCampaign = get_smscampaign_model()

# Function views --------------------------------------------------------------


# def abstract_add_smscampaign(request, form=camp_forms.CampaignCreateForm,
#                              submit_label=SMSCampaign.save_label,
#                             ):
#     warnings.warn('sms.views.campaign.abstract_add_smscampaign() is deprecated ; '
#                   'use the class-based view SMSCampaignCreation instead.',
#                   DeprecationWarning
#                  )
#     return generic.add_entity(request, form,
#                               extra_template_dict={'submit_label': submit_label},
#                              )


# def abstract_edit_smscampaign(request, campaign_id, form=camp_forms.CampaignEditForm):
#     warnings.warn('sms.views.campaign.abstract_edit_smscampaign() is deprecated ; '
#                   'use the class-based view SMSCampaignEdition instead.',
#                   DeprecationWarning
#                  )
#     return generic.edit_entity(request, campaign_id, SMSCampaign, form)


# def abstract_view_smscampaign(request, campaign_id,
#                               template='sms/view_campaign.html',
#                              ):
#     warnings.warn('sms.views.campaign.abstract_view_smscampaign() is deprecated ; '
#                   'use the class-based view SMSCampaignDetail instead.',
#                   DeprecationWarning
#                  )
#     return generic.view_entity(request, campaign_id, SMSCampaign, template=template)


# @login_required
# @permission_required(('sms', cperm(SMSCampaign)))
# def add(request):
#     warnings.warn('sms.views.campaign.add() is deprecated.', DeprecationWarning)
#     return abstract_add_smscampaign(request)


# @login_required
# @permission_required('sms')
# def edit(request, campaign_id):
#     warnings.warn('sms.views.campaign.edit() is deprecated.', DeprecationWarning)
#     return abstract_edit_smscampaign(request, campaign_id)


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


# @login_required
# @permission_required('sms')
# def detailview(request, campaign_id):
#     warnings.warn('sms.views.campaign.detailview() is deprecated.', DeprecationWarning)
#     return abstract_view_smscampaign(request, campaign_id)


# @login_required
# @permission_required('sms')
# def listview(request):
#     return generic.list_view(request, SMSCampaign, hf_pk=DEFAULT_HFILTER_SMSCAMPAIGN)



@login_required
@permission_required('sms')
def delete_messaging_list(request, campaign_id):
    campaign = get_object_or_404(SMSCampaign, pk=campaign_id)
    request.user.has_perm_to_change_or_die(campaign)

    campaign.lists.remove(request.POST.get('id'))

    if request.is_ajax():
        return HttpResponse()

    return redirect(campaign)


# Class-based views  ----------------------------------------------------------

class SMSCampaignCreation(generic.EntityCreation):
    model = SMSCampaign
    form_class = camp_forms.CampaignCreateForm


class SMSCampaignDetail(generic.EntityDetail):
    model = SMSCampaign
    template_name = 'sms/view_campaign.html'
    pk_url_kwarg = 'campaign_id'


class SMSCampaignEdition(generic.EntityEdition):
    model = SMSCampaign
    form_class = camp_forms.CampaignEditForm
    pk_url_kwarg = 'campaign_id'


class MessagingListsAdding(generic.AddingInstanceToEntityPopup):
    # model = MessagingList
    form_class = camp_forms.CampaignAddListForm
    template_name = 'creme_core/generics/blockform/link-popup.html'
    title = _('New messaging lists for «{entity}»')
    submit_label = _('Link the messaging lists')
    entity_id_url_kwarg = 'campaign_id'
    entity_classes = SMSCampaign


class SMSCampaignsList(generic.EntitiesList):
    model = SMSCampaign
    default_headerfilter_id = DEFAULT_HFILTER_SMSCAMPAIGN
