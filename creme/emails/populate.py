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

from creme_core.models import RelationType, SearchConfigItem, ButtonMenuItem, HeaderFilterItem, HeaderFilter
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
        RelationType.create((REL_SUB_MAIL_RECEIVED, _(u"(email) received by"), [EntityEmail]),
                            (REL_OBJ_MAIL_RECEIVED, _(u"received the email"),  [Organisation, Contact]))

        RelationType.create((REL_SUB_MAIL_SENDED, _(u"(email) sended"),   [EntityEmail]),
                            (REL_OBJ_MAIL_SENDED, _(u"sended the email"), [Organisation, Contact]))

        hf = HeaderFilter.create(pk='emails-hf_mailinglist', name=_(u"Mailing list view"), model=MailingList)
        hf.set_items([HeaderFilterItem.build_4_field(model=MailingList, name='name')])

        hf = HeaderFilter.create(pk='emails-hf_campaign', name=_(u"Campaign view"), model=EmailCampaign)
        hf.set_items([HeaderFilterItem.build_4_field(model=EmailCampaign, name='name')])

        hf   = HeaderFilter.create(pk='emails-hf_template', name=_(u"Email template view"), model=EmailTemplate)
        hf.set_items([HeaderFilterItem.build_4_field(model=EmailTemplate, name='name'),
                      HeaderFilterItem.build_4_field(model=EmailTemplate, name='subject'),
                     ])

        hf   = HeaderFilter.create(pk='emails-hf_email', name=_(u"Email view"), model=EntityEmail)
        hf.set_items([HeaderFilterItem.build_4_field(model=EntityEmail, name='sender'),
                      HeaderFilterItem.build_4_field(model=EntityEmail, name='recipient'),
                      HeaderFilterItem.build_4_field(model=EntityEmail, name='subject'),
                     ])

        ButtonMenuItem.create(pk='emails-entity_email_link_button', model=EntityEmail, button=entityemail_link_button, order=20)

        SearchConfigItem.create(EmailCampaign, ['name', 'mailing_lists__name'])
        SearchConfigItem.create(MailingList,   ['name', 'children__name', 'contacts__first_name', 'contacts__last_name', 'organisations__name'])
        SearchConfigItem.create(EmailTemplate, ['name', 'subject', 'body', 'attachments__title'])
        SearchConfigItem.create(EntityEmail,   ['sender', 'recipient', 'subject'])
