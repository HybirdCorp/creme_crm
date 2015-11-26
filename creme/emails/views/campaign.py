# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views.generic import (add_entity, add_to_entity,
        edit_entity, view_entity, list_view)
from creme.creme_core.utils import get_from_POST_or_404

from .. import get_emailcampaign_model
from ..constants import DEFAULT_HFILTER_CAMPAIGN
from ..forms.campaign import CampaignCreateForm, CampaignEditForm, CampaignAddMLForm
#from ..models import EmailCampaign


EmailCampaign = get_emailcampaign_model()


def abstract_add_campaign(request, form=CampaignCreateForm,
                          submit_label=_('Save the emailing campaign'),
                         ):
    return add_entity(request, form,
                      extra_template_dict={'submit_label': submit_label},
                     )


def abstract_edit_campaign(request, campaign_id, form=CampaignEditForm):
    return edit_entity(request, campaign_id, EmailCampaign, form)


def abstract_view_campaign(request, campaign_id,
                           template='emails/view_campaign.html'
                          ):
    return view_entity(request, campaign_id, EmailCampaign,
                       # path='/emails/campaign',
                       template=template,
                      )


@login_required
# @permission_required(('emails', 'emails.add_emailcampaign'))
@permission_required(('emails', cperm(EmailCampaign)))
def add(request):
    return abstract_add_campaign(request)


@login_required
@permission_required('emails')
def edit(request, campaign_id):
    return abstract_edit_campaign(request, campaign_id)


@login_required
@permission_required('emails')
def detailview(request, campaign_id):
    return abstract_view_campaign(request, campaign_id)


@login_required
@permission_required('emails')
def listview(request):
    return list_view(request, EmailCampaign, hf_pk=DEFAULT_HFILTER_CAMPAIGN,
                     # extra_dict={'add_url': '/emails/campaign/add'}
                     # extra_dict={'add_url': reverse('emails__create_campaign')},
                    )


@login_required
@permission_required('emails')
def add_ml(request, campaign_id):
    return add_to_entity(request, campaign_id, CampaignAddMLForm,
                         ugettext(u'New mailing lists for «%s»'),
                         entity_class=EmailCampaign,
                         submit_label=_('Link the mailing lists'),
                        )


@login_required
@permission_required('emails')
def delete_ml(request, campaign_id):
    ml_id    = get_from_POST_or_404(request.POST, 'id')
    campaign = get_object_or_404(EmailCampaign, pk=campaign_id)

    request.user.has_perm_to_change_or_die(campaign)

    campaign.mailing_lists.remove(ml_id)

    if request.is_ajax():
        return HttpResponse("", content_type="text/javascript")

    return redirect(campaign)
