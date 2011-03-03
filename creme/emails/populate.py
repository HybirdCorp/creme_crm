# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from creme_core.models import SearchConfigItem, RelationType
from creme_core.models.button_menu import ButtonMenuItem
from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD
from creme_core.utils import create_or_update as create
from creme_core.management.commands.creme_populate import BasePopulator

from persons.models import Organisation, Contact

from emails.models import MailingList, EmailCampaign, EmailTemplate, EntityEmail
from emails.buttons import entityemail_link_button
from emails.constants import (REL_SUB_MAIL_RECEIVED, REL_OBJ_MAIL_RECEIVED,
                              REL_SUB_MAIL_SENDED, REL_OBJ_MAIL_SENDED)


class Populator(BasePopulator):
    dependencies = ['creme.creme_core']

    def populate(self, *args, **kwargs):
        get_ct = ContentType.objects.get_for_model

        RelationType.create((REL_SUB_MAIL_RECEIVED, _(u"(email) received by"), [EntityEmail]),
                            (REL_OBJ_MAIL_RECEIVED, _(u"received the email"), [Organisation, Contact]))

        RelationType.create((REL_SUB_MAIL_SENDED, _(u"(email) sended"), [EntityEmail]),
                            (REL_OBJ_MAIL_SENDED, _(u"sended the email"), [Organisation, Contact]))

        hf = create(HeaderFilter, 'emails-hf_mailinglist', name=_(u'Mailing list view'), entity_type=get_ct(MailingList), is_custom=False)
        create(HeaderFilterItem, 'emails-hfi_mailinglist_name', order=1, name='name', title=_(u'Name'), type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True, filter_string="name__icontains")

        hf = create(HeaderFilter, 'emails-hf_campaign', name=_(u'Campaign view'), entity_type=get_ct(EmailCampaign), is_custom=False)
        create(HeaderFilterItem, 'emails-hfi_campaign_name', order=1, name='name', title=_(u'Name'), type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True, filter_string="name__icontains")

        hf = create(HeaderFilter, 'emails-hf_template', name=_(u'Email template view'), entity_type=get_ct(EmailTemplate), is_custom=False)
        pref = 'emails-hfi_template'
        create(HeaderFilterItem, pref + 'name',    order=1, name='name',    title=_(u'Name'),    type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True, filter_string="name__icontains")
        create(HeaderFilterItem, pref + 'subject', order=2, name='subject', title=_(u'Subject'), type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True, filter_string="subject__icontains")

        hf = create(HeaderFilter, 'emails-hf_email', name=_(u'Email view'), entity_type=get_ct(EntityEmail), is_custom=False)
        pref = 'emails-hfi_email_'
        create(HeaderFilterItem, pref + 'sender',    order=1, name='sender',    title=_(u'Sender'),    type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True, filter_string="sender__icontains")
        create(HeaderFilterItem, pref + 'recipient', order=2, name='recipient', title=_(u'Recipient'), type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True, filter_string="recipient__icontains")
        create(HeaderFilterItem, pref + 'subject',   order=3, name='subject',   title=_(u'Subject'),   type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True, filter_string="subject__icontains")

        create(ButtonMenuItem, 'emails-entity_email_link_button', content_type=get_ct(EntityEmail), button_id=entityemail_link_button.id_, order=20)

        SearchConfigItem.create(EmailCampaign, ['name', 'mailing_lists__name'])
        SearchConfigItem.create(MailingList,   ['name', 'children__name', 'contacts__first_name', 'contacts__last_name', 'organisations__name'])
        SearchConfigItem.create(EmailTemplate, ['name', 'subject', 'body', 'attachments__title'])
        SearchConfigItem.create(EntityEmail,   ['sender', 'recipient', 'subject',])

