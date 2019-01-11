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

import warnings

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic

from .. import get_emailcampaign_model
from ..constants import DEFAULT_HFILTER_CAMPAIGN
from ..forms import campaign as camp_forms


EmailCampaign = get_emailcampaign_model()

# Function views --------------------------------------------------------------


def abstract_add_campaign(request, form=camp_forms.CampaignCreateForm,
                          submit_label=EmailCampaign.save_label,
                         ):
    warnings.warn('emails.views.campaign.abstract_add_campaign() is deprecated ; '
                  'use the class-based view EmailCampaignCreation instead.',
                  DeprecationWarning
                 )
    return generic.add_entity(request, form,
                              extra_template_dict={'submit_label': submit_label},
                             )


def abstract_edit_campaign(request, campaign_id, form=camp_forms.CampaignEditForm):
    warnings.warn('emails.views.campaign.abstract_edit_campaign() is deprecated ; '
                  'use the class-based view EmailCampaignEdition instead.',
                  DeprecationWarning
                 )
    return generic.edit_entity(request, campaign_id, EmailCampaign, form)


def abstract_view_campaign(request, campaign_id,
                           template='emails/view_campaign.html'
                          ):
    warnings.warn('emails.views.campaign.abstract_view_campaign() is deprecated ; '
                  'use the class-based view EmailCampaignDetail instead.',
                  DeprecationWarning
                 )
    return generic.view_entity(request, campaign_id, EmailCampaign, template=template)


@login_required
@permission_required(('emails', cperm(EmailCampaign)))
def add(request):
    warnings.warn('emails.views.campaign.add() is deprecated.', DeprecationWarning)
    return abstract_add_campaign(request)


@login_required
@permission_required('emails')
def edit(request, campaign_id):
    warnings.warn('emails.views.campaign.edit() is deprecated.', DeprecationWarning)
    return abstract_edit_campaign(request, campaign_id)


@login_required
@permission_required('emails')
def detailview(request, campaign_id):
    warnings.warn('emails.views.campaign.detailview() is deprecated.', DeprecationWarning)
    return abstract_view_campaign(request, campaign_id)


@login_required
@permission_required('emails')
def listview(request):
    return generic.list_view(request, EmailCampaign, hf_pk=DEFAULT_HFILTER_CAMPAIGN)


@login_required
@permission_required('emails')
def delete_ml(request, campaign_id):
    ml_id    = get_from_POST_or_404(request.POST, 'id')
    campaign = get_object_or_404(EmailCampaign, pk=campaign_id)

    request.user.has_perm_to_change_or_die(campaign)

    campaign.mailing_lists.remove(ml_id)

    if request.is_ajax():
        return HttpResponse()

    return redirect(campaign)


# Class-based views  ----------------------------------------------------------

class EmailCampaignCreation(generic.EntityCreation):
    model = EmailCampaign
    form_class = camp_forms.CampaignCreateForm


class EmailCampaignDetail(generic.EntityDetail):
    model = EmailCampaign
    template_name = 'emails/view_campaign.html'
    pk_url_kwarg = 'campaign_id'


class EmailCampaignEdition(generic.EntityEdition):
    model = EmailCampaign
    form_class = camp_forms.CampaignEditForm
    pk_url_kwarg = 'campaign_id'


class MailingListsAdding(generic.RelatedToEntityFormPopup):
    # model = MailingList
    form_class = camp_forms.CampaignAddMLForm
    template_name = 'creme_core/generics/blockform/link-popup.html'
    title = _('New mailing lists for «{entity}»')
    submit_label = _('Link the mailing lists')
    entity_id_url_kwarg = 'campaign_id'
    entity_classes = EmailCampaign
