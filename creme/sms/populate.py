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

from django.contrib.contenttypes.models import ContentType

from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD
from creme_core.utils import create_or_update_models_instance as create
from creme_core.management.commands.creme_populate import BasePopulator

from sms.models import SendList, SMSCampaign, MessageTemplate


class Populator(BasePopulator):
    dependencies = ['creme.core']

    def populate(self, *args, **kwargs):
        get_ct = ContentType.objects.get_for_model

        hf_id = create(HeaderFilter, 'sms-hf_sendlist', name=u'Vue de Liste de Diffusion', entity_type_id=get_ct(SendList).id, is_custom=False).id
        create(HeaderFilterItem, 'sms-hf_sendlist_name', order=1, name='name', title=u'Nom', type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, filter_string="name__icontains")

        hf_id = create(HeaderFilter, 'sms-hf_campaign', name=u'Vue de Campagne', entity_type_id=get_ct(SMSCampaign).id, is_custom=False).id
        create(HeaderFilterItem, 'sms-hf_campaign_name', order=1, name='name', title=u'Nom', type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, filter_string="name__icontains")

        hf_id = create(HeaderFilter, 'sms-hf_template', name=u'Vue de Template', entity_type_id=get_ct(MessageTemplate).id, is_custom=False).id
        create(HeaderFilterItem, 'sms-hf_template_name', order=1, name='name', title=u'Nom', type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, filter_string="name__icontains")

        #hf_id = create(HeaderFilter, 'sms-hf_template', name='Vue de patron de mail', entity_type_id=get_ct(EmailTemplate).id, is_custom=False).id
        #create(HeaderFilterItem, 'sms-hf_template_name',    order=1, name='name',    title=u'Nom',   type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, filter_string="name__icontains")
        #create(HeaderFilterItem, 'sms-hf_template_subject', order=2, name='subject', title=u'Sujet', type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, filter_string="subject__icontains")
