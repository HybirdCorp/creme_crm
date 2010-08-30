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

from django.utils.translation import ugettext as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models import SearchConfigItem, SearchField, RelationType
from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD
from creme_core.utils import create_or_update_models_instance as create
from creme_core.utils.meta import get_verbose_field_name
from creme_core.management.commands.creme_populate import BasePopulator

from emails.models import MailingList, EmailCampaign, EmailTemplate, EntityEmail
from emails.constants import REL_SUB_MAIL_RECEIVED, REL_OBJ_MAIL_RECEIVED


class Populator(BasePopulator):
    dependencies = ['creme.core']

    def populate(self, *args, **kwargs):
        get_ct = ContentType.objects.get_for_model

        RelationType.create((REL_SUB_MAIL_RECEIVED, _(u"(email) received by"), [EntityEmail]),
                            (REL_OBJ_MAIL_RECEIVED, _(u"received the email")))

        hf_id = create(HeaderFilter, 'emails-hf_mailinglist', name=_(u'Mailing list view'), entity_type_id=get_ct(MailingList).id, is_custom=False).id
        create(HeaderFilterItem, 'emails-hf_mailinglist_name', order=1, name='name', title=_(u'Name'), type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, filter_string="name__icontains")

        hf_id = create(HeaderFilter, 'emails-hf_campaign', name=_(u'Campaign view'), entity_type_id=get_ct(EmailCampaign).id, is_custom=False).id
        create(HeaderFilterItem, 'emails-hf_campaign_name', order=1, name='name', title=_(u'Name'), type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, filter_string="name__icontains")

        hf_id = create(HeaderFilter, 'emails-hf_template', name=_(u'Email template view'), entity_type_id=get_ct(EmailTemplate).id, is_custom=False).id
        create(HeaderFilterItem, 'emails-hf_template_name',    order=1, name='name',    title=_(u'Name'),    type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, filter_string="name__icontains")
        create(HeaderFilterItem, 'emails-hf_template_subject', order=2, name='subject', title=_(u'Subject'), type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, filter_string="subject__icontains")


        #m2m fields excluded for the moment see creme_config/forms/search.py
        model = EmailCampaign
        sci = create(SearchConfigItem, content_type_id=ContentType.objects.get_for_model(model).id)
        SCI_pk = sci.pk
        sci_fields = ['name', ]#'mailing_lists__name']
        for i, field in enumerate(sci_fields):
            create(SearchField, field=field, field_verbose_name=get_verbose_field_name(model, field), order=i, search_config_item_id=SCI_pk)

        model = MailingList
        sci = create(SearchConfigItem, content_type_id=ContentType.objects.get_for_model(model).id)
        SCI_pk = sci.pk
        sci_fields = ['name', ]#'children__name', 'contacts__first_name', 'contacts__last_name', 'organisations__name']
        for i, field in enumerate(sci_fields):
            create(SearchField, field=field, field_verbose_name=get_verbose_field_name(model, field), order=i, search_config_item_id=SCI_pk)

        model = EmailTemplate
        sci = create(SearchConfigItem, content_type_id=ContentType.objects.get_for_model(model).id)
        SCI_pk = sci.pk
        sci_fields = ['name', 'subject', 'body',]# 'attachments__title']
        for i, field in enumerate(sci_fields):
            create(SearchField, field=field, field_verbose_name=get_verbose_field_name(model, field), order=i, search_config_item_id=SCI_pk)
