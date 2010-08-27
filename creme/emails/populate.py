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

from creme_core.models import SearchConfigItem, RelationType
from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD
from creme_core.utils import create_or_update_models_instance as create
from creme_core.management.commands.creme_populate import BasePopulator

from emails.models import MailingList, EmailCampaign, EmailTemplate, EntityEmail
from emails.constants import REL_SUB_MAIL_RECEIVED, REL_OBJ_MAIL_RECEIVED


class Populator(BasePopulator):
    dependencies = ['creme.core']

    def populate(self, *args, **kwargs):
        get_ct = ContentType.objects.get_for_model

        RelationType.create((REL_SUB_MAIL_RECEIVED, u"l'email a été reçu(e) par", [EntityEmail]),
                            (REL_OBJ_MAIL_RECEIVED, u"a reçu l'email"))

        hf_id = create(HeaderFilter, 'emails-hf_mailinglist', name=u'Vue de Liste de Diffusion', entity_type_id=get_ct(MailingList).id, is_custom=False).id
        create(HeaderFilterItem, 'emails-hf_mailinglist_name', order=1, name='name', title=u'Nom', type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, filter_string="name__icontains")

        hf_id = create(HeaderFilter, 'emails-hf_campaign', name=u'Vue de Campagne', entity_type_id=get_ct(EmailCampaign).id, is_custom=False).id
        create(HeaderFilterItem, 'emails-hf_campaign_name', order=1, name='name', title=u'Nom', type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, filter_string="name__icontains")

        hf_id = create(HeaderFilter, 'emails-hf_template', name='Vue de patron de mail', entity_type_id=get_ct(EmailTemplate).id, is_custom=False).id
        create(HeaderFilterItem, 'emails-hf_template_name',    order=1, name='name',    title=u'Nom',   type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, filter_string="name__icontains")
        create(HeaderFilterItem, 'emails-hf_template_subject', order=2, name='subject', title=u'Sujet', type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, filter_string="subject__icontains")

        hf_id = create(HeaderFilter, 'emails-hf_email', name='Vue des mail', entity_type_id=get_ct(EntityEmail).id, is_custom=False).id
        create(HeaderFilterItem, 'emails-hf_email_sender',    order=1, name='sender',    title=u'Expediteur',   type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, filter_string="sender__icontains")
        create(HeaderFilterItem, 'emails-hf_email_recipient', order=2, name='recipient', title=u'Destinataire', type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, filter_string="recipient__icontains")
        create(HeaderFilterItem, 'emails-hf_email_subject',   order=3, name='subject',   title=u'Sujet',        type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, filter_string="subject__icontains")


        #m2m fields excluded for the moment see creme_config/forms/search.py
        SearchConfigItem.create(EmailCampaign, ['name', ])#'mailing_lists__name']
        SearchConfigItem.create(MailingList,   ['name', ])#'children__name', 'contacts__first_name', 'contacts__last_name', 'organisations__name']
        SearchConfigItem.create(EmailTemplate, ['name', 'subject', 'body',])# 'attachments__title']
        SearchConfigItem.create(EntityEmail,   ['sender', 'recipient', 'subject',])

