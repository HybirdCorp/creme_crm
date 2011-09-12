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

from logging import info

from django.utils.translation import ugettext as _
from django.conf import settings

from creme_core.models import (RelationType, SearchConfigItem,
                               BlockDetailviewLocation, BlockPortalLocation,
                               ButtonMenuItem, HeaderFilterItem, HeaderFilter)
from creme_core.blocks import properties_block, relations_block, customfields_block, history_block
from creme_core.management.commands.creme_populate import BasePopulator

from persons.models import Organisation, Contact

from emails.models import MailingList, EmailCampaign, EmailTemplate, EntityEmail
from emails.blocks import *
from emails.buttons import entityemail_link_button
from emails.constants import (REL_SUB_MAIL_RECEIVED, REL_OBJ_MAIL_RECEIVED,
                              REL_SUB_MAIL_SENDED, REL_OBJ_MAIL_SENDED, REL_SUB_RELATED_TO, REL_OBJ_RELATED_TO)


class Populator(BasePopulator):
    dependencies = ['creme_core']

    def populate(self, *args, **kwargs):
        RelationType.create((REL_SUB_MAIL_RECEIVED, _(u"(email) received by"), [EntityEmail]),
                            (REL_OBJ_MAIL_RECEIVED, _(u"received the email"),  [Organisation, Contact]))
        RelationType.create((REL_SUB_MAIL_SENDED, _(u"(email) sended"),        [EntityEmail]),
                            (REL_OBJ_MAIL_SENDED, _(u"sended the email"),      [Organisation, Contact]))
        RelationType.create((REL_SUB_RELATED_TO, _(u'(email) related to'),     [EntityEmail]),
                            (REL_OBJ_RELATED_TO, _(u'related to the email'),   []))

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

        BlockDetailviewLocation.create_4_model_block(order=5, zone=BlockDetailviewLocation.LEFT, model=MailingList)
        BlockDetailviewLocation.create(block_id=customfields_block.id_,     order=40,  zone=BlockDetailviewLocation.LEFT,  model=MailingList)
        BlockDetailviewLocation.create(block_id=email_recipients_block.id_, order=80,  zone=BlockDetailviewLocation.LEFT,  model=MailingList)
        BlockDetailviewLocation.create(block_id=contacts_block.id_,         order=90,  zone=BlockDetailviewLocation.LEFT,  model=MailingList)
        BlockDetailviewLocation.create(block_id=organisations_block.id_,    order=95,  zone=BlockDetailviewLocation.LEFT,  model=MailingList)
        BlockDetailviewLocation.create(block_id=child_lists_block.id_,      order=100, zone=BlockDetailviewLocation.LEFT,  model=MailingList)
        BlockDetailviewLocation.create(block_id=parent_lists_block.id_,     order=105, zone=BlockDetailviewLocation.LEFT,  model=MailingList)
        BlockDetailviewLocation.create(block_id=properties_block.id_,       order=450, zone=BlockDetailviewLocation.LEFT,  model=MailingList)
        BlockDetailviewLocation.create(block_id=relations_block.id_,        order=500, zone=BlockDetailviewLocation.LEFT,  model=MailingList)
        BlockDetailviewLocation.create(block_id=history_block.id_,          order=20,  zone=BlockDetailviewLocation.RIGHT, model=MailingList)

        BlockDetailviewLocation.create(block_id=sendings_block.id_,      order=2,   zone=BlockDetailviewLocation.TOP,   model=EmailCampaign)
        BlockDetailviewLocation.create_4_model_block(order=5, zone=BlockDetailviewLocation.LEFT, model=EmailCampaign)
        BlockDetailviewLocation.create(block_id=customfields_block.id_,  order=40,  zone=BlockDetailviewLocation.LEFT,  model=EmailCampaign)
        BlockDetailviewLocation.create(block_id=mailing_lists_block.id_, order=120, zone=BlockDetailviewLocation.LEFT,  model=EmailCampaign)
        BlockDetailviewLocation.create(block_id=properties_block.id_,    order=450, zone=BlockDetailviewLocation.LEFT,  model=EmailCampaign)
        BlockDetailviewLocation.create(block_id=relations_block.id_,     order=500, zone=BlockDetailviewLocation.LEFT,  model=EmailCampaign)
        BlockDetailviewLocation.create(block_id=history_block.id_,       order=20,  zone=BlockDetailviewLocation.RIGHT, model=EmailCampaign)

        BlockDetailviewLocation.create_4_model_block(order=5, zone=BlockDetailviewLocation.LEFT, model=EmailTemplate)
        BlockDetailviewLocation.create(block_id=customfields_block.id_,  order=40,  zone=BlockDetailviewLocation.LEFT,  model=EmailTemplate)
        BlockDetailviewLocation.create(block_id=attachments_block.id_,   order=60,  zone=BlockDetailviewLocation.LEFT,  model=EmailTemplate)
        BlockDetailviewLocation.create(block_id=properties_block.id_,    order=450, zone=BlockDetailviewLocation.LEFT,  model=EmailTemplate)
        BlockDetailviewLocation.create(block_id=relations_block.id_,     order=500, zone=BlockDetailviewLocation.LEFT,  model=EmailTemplate)
        BlockDetailviewLocation.create(block_id=history_block.id_,       order=20,  zone=BlockDetailviewLocation.RIGHT, model=EmailTemplate)

        #'persons' app
        BlockDetailviewLocation.create(block_id=mails_history_block.id_, order=600, zone=BlockDetailviewLocation.RIGHT, model=Contact)
        BlockDetailviewLocation.create(block_id=mails_history_block.id_, order=600, zone=BlockDetailviewLocation.RIGHT, model=Organisation)

        BlockPortalLocation.create(app_name='emails', block_id=signatures_block.id_, order=10)
        BlockPortalLocation.create(app_name='emails', block_id=history_block.id_,    order=30)

        if 'assistants' in settings.INSTALLED_APPS:
            info('Assistants app is installed => we use the assistants blocks on detail views')

            from assistants.blocks import alerts_block, memos_block, todos_block, messages_block

            for model in (MailingList, EmailCampaign, EmailTemplate):
                BlockDetailviewLocation.create(block_id=todos_block.id_,    order=100, zone=BlockDetailviewLocation.RIGHT, model=model)
                BlockDetailviewLocation.create(block_id=memos_block.id_,    order=200, zone=BlockDetailviewLocation.RIGHT, model=model)
                BlockDetailviewLocation.create(block_id=alerts_block.id_,   order=300, zone=BlockDetailviewLocation.RIGHT, model=model)
                BlockDetailviewLocation.create(block_id=messages_block.id_, order=400, zone=BlockDetailviewLocation.RIGHT, model=model)

            BlockPortalLocation.create(app_name='emails', block_id=memos_block.id_,    order=100)
            BlockPortalLocation.create(app_name='emails', block_id=alerts_block.id_,   order=200)
            BlockPortalLocation.create(app_name='emails', block_id=messages_block.id_, order=300)

        ButtonMenuItem.create(pk='emails-entity_email_link_button', model=EntityEmail, button=entityemail_link_button, order=20)

        SearchConfigItem.create(EmailCampaign, ['name', 'mailing_lists__name'])
        SearchConfigItem.create(MailingList,   ['name', 'children__name', 'contacts__first_name', 'contacts__last_name', 'organisations__name'])
        SearchConfigItem.create(EmailTemplate, ['name', 'subject', 'body', 'attachments__title'])
        SearchConfigItem.create(EntityEmail,   ['sender', 'recipient', 'subject'])
