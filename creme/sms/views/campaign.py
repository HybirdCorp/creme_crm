################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from django.db.transaction import atomic
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.workflow import run_workflow_engine
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic

from .. import custom_forms, get_smscampaign_model
from ..constants import DEFAULT_HFILTER_SMSCAMPAIGN
from ..forms import campaign as camp_forms

SMSCampaign = get_smscampaign_model()


class MessagingListRemoving(generic.base.EntityRelatedMixin, generic.CremeDeletion):
    permissions = 'sms'
    entity_classes = SMSCampaign
    entity_id_url_kwarg = 'campaign_id'

    mlist_id_arg = 'id'

    def perform_deletion(self, request):
        ml_id = get_from_POST_or_404(request.POST, self.mlist_id_arg, cast=int)

        with atomic(), run_workflow_engine(user=request.user):
            self.get_related_entity().lists.remove(ml_id)


class SMSCampaignCreation(generic.EntityCreation):
    model = SMSCampaign
    form_class = custom_forms.CAMPAIGN_CREATION_CFORM


class SMSCampaignDetail(generic.EntityDetail):
    model = SMSCampaign
    template_name = 'sms/view_campaign.html'
    pk_url_kwarg = 'campaign_id'


class SMSCampaignEdition(generic.EntityEdition):
    model = SMSCampaign
    form_class = custom_forms.CAMPAIGN_EDITION_CFORM
    pk_url_kwarg = 'campaign_id'


class MessagingListsAdding(generic.RelatedToEntityFormPopup):
    form_class = camp_forms.CampaignAddListForm
    template_name = 'creme_core/generics/blockform/link-popup.html'
    title = _('New messaging lists for «{entity}»')
    submit_label = _('Link the messaging lists')
    entity_id_url_kwarg = 'campaign_id'
    entity_classes = SMSCampaign


class SMSCampaignsList(generic.EntitiesList):
    model = SMSCampaign
    default_headerfilter_id = DEFAULT_HFILTER_SMSCAMPAIGN
