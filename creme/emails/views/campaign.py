# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from django.utils.translation import gettext_lazy as _

from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic

from .. import custom_forms, get_emailcampaign_model
from ..constants import DEFAULT_HFILTER_CAMPAIGN
from ..forms import campaign as camp_forms

EmailCampaign = get_emailcampaign_model()


class EmailCampaignCreation(generic.EntityCreation):
    model = EmailCampaign
    form_class = custom_forms.CAMPAIGN_CREATION_CFORM


class EmailCampaignDetail(generic.EntityDetail):
    model = EmailCampaign
    template_name = 'emails/view_campaign.html'
    pk_url_kwarg = 'campaign_id'


class EmailCampaignEdition(generic.EntityEdition):
    model = EmailCampaign
    form_class = custom_forms.CAMPAIGN_EDITION_CFORM
    pk_url_kwarg = 'campaign_id'


class EmailCampaignsList(generic.EntitiesList):
    model = EmailCampaign
    default_headerfilter_id = DEFAULT_HFILTER_CAMPAIGN


class MailingListsAdding(generic.RelatedToEntityFormPopup):
    # model = MailingList
    form_class = camp_forms.CampaignAddMLForm
    template_name = 'creme_core/generics/blockform/link-popup.html'
    title = _('New mailing lists for «{entity}»')
    submit_label = _('Link the mailing lists')
    entity_id_url_kwarg = 'campaign_id'
    entity_classes = EmailCampaign


class MailingListRemoving(generic.base.EntityRelatedMixin, generic.CremeDeletion):
    permissions = 'emails'
    entity_classes = EmailCampaign
    entity_id_url_kwarg = 'campaign_id'

    ml_id_arg = 'id'

    def perform_deletion(self, request):
        ml_id = get_from_POST_or_404(request.POST, self.ml_id_arg, cast=int)
        self.get_related_entity().mailing_lists.remove(ml_id)
