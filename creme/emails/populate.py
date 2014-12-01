# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

import logging

from django.conf import settings
from django.utils.translation import ugettext as _

from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.blocks import (properties_block, relations_block,
        customfields_block, history_block)
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (RelationType, SearchConfigItem,
        BlockDetailviewLocation, BlockPortalLocation, ButtonMenuItem, HeaderFilter)

from creme.persons.models import Organisation, Contact

from .models import MailingList, EmailCampaign, EmailTemplate, EntityEmail
from .blocks import *
from .buttons import entityemail_link_button
from .constants import (REL_SUB_MAIL_RECEIVED, REL_OBJ_MAIL_RECEIVED,
        REL_SUB_MAIL_SENDED, REL_OBJ_MAIL_SENDED, REL_SUB_RELATED_TO, REL_OBJ_RELATED_TO)


logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core', 'persons']

    def populate(self):
        already_populated = RelationType.objects.filter(pk=REL_SUB_MAIL_RECEIVED).exists()


        RelationType.create((REL_SUB_MAIL_RECEIVED, _(u"(email) received by"),  [EntityEmail]),
                            (REL_OBJ_MAIL_RECEIVED, _(u"received the email"),   [Organisation, Contact]))
        RelationType.create((REL_SUB_MAIL_SENDED,   _(u"(email) sended"),       [EntityEmail]),
                            (REL_OBJ_MAIL_SENDED,   _(u"sended the email"),     [Organisation, Contact]))
        RelationType.create((REL_SUB_RELATED_TO,    _(u'(email) related to'),   [EntityEmail]),
                            (REL_OBJ_RELATED_TO,    _(u'related to the email'), []))


        create_hf = HeaderFilter.create
        create_hf(pk='emails-hf_mailinglist', name=_(u"Mailing list view"), model=MailingList,
                  cells_desc=[(EntityCellRegularField, {'name': 'name'})],
                 )
        create_hf(pk='emails-hf_campaign', name=_(u"Campaign view"), model=EmailCampaign,
                  cells_desc=[(EntityCellRegularField, {'name': 'name'})],
                 )
        create_hf(pk='emails-hf_template', name=_(u"Email template view"), model=EmailTemplate,
                  cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                              (EntityCellRegularField, {'name': 'subject'}),
                             ],
                 )
        create_hf(pk='emails-hf_email', name=_(u"Email view"), model=EntityEmail,
                  cells_desc=[(EntityCellRegularField, {'name': 'sender'}),
                              (EntityCellRegularField, {'name': 'recipient'}),
                              (EntityCellRegularField, {'name': 'subject'}),
                             ],
                 )


        create_searchconf = SearchConfigItem.create_if_needed
        create_searchconf(EmailCampaign, ['name', 'mailing_lists__name'])
        create_searchconf(MailingList,   ['name', 'children__name', 'contacts__first_name', 'contacts__last_name', 'organisations__name'])
        create_searchconf(EmailTemplate, ['name', 'subject', 'body', 'attachments__title'])
        create_searchconf(EntityEmail,   ['sender', 'recipient', 'subject'])


        if not already_populated:
            create_bdl = BlockDetailviewLocation.create
            BlockDetailviewLocation.create_4_model_block(order=5,      zone=BlockDetailviewLocation.LEFT,  model=MailingList)
            create_bdl(block_id=customfields_block.id_,     order=40,  zone=BlockDetailviewLocation.LEFT,  model=MailingList)
            create_bdl(block_id=email_recipients_block.id_, order=80,  zone=BlockDetailviewLocation.LEFT,  model=MailingList)
            create_bdl(block_id=contacts_block.id_,         order=90,  zone=BlockDetailviewLocation.LEFT,  model=MailingList)
            create_bdl(block_id=organisations_block.id_,    order=95,  zone=BlockDetailviewLocation.LEFT,  model=MailingList)
            create_bdl(block_id=child_lists_block.id_,      order=100, zone=BlockDetailviewLocation.LEFT,  model=MailingList)
            create_bdl(block_id=parent_lists_block.id_,     order=105, zone=BlockDetailviewLocation.LEFT,  model=MailingList)
            create_bdl(block_id=properties_block.id_,       order=450, zone=BlockDetailviewLocation.LEFT,  model=MailingList)
            create_bdl(block_id=relations_block.id_,        order=500, zone=BlockDetailviewLocation.LEFT,  model=MailingList)
            create_bdl(block_id=history_block.id_,          order=20,  zone=BlockDetailviewLocation.RIGHT, model=MailingList)

            create_bdl(block_id=sendings_block.id_,      order=2,   zone=BlockDetailviewLocation.TOP,   model=EmailCampaign)
            BlockDetailviewLocation.create_4_model_block(order=5,   zone=BlockDetailviewLocation.LEFT,  model=EmailCampaign)
            create_bdl(block_id=customfields_block.id_,  order=40,  zone=BlockDetailviewLocation.LEFT,  model=EmailCampaign)
            create_bdl(block_id=mailing_lists_block.id_, order=120, zone=BlockDetailviewLocation.LEFT,  model=EmailCampaign)
            create_bdl(block_id=properties_block.id_,    order=450, zone=BlockDetailviewLocation.LEFT,  model=EmailCampaign)
            create_bdl(block_id=relations_block.id_,     order=500, zone=BlockDetailviewLocation.LEFT,  model=EmailCampaign)
            create_bdl(block_id=history_block.id_,       order=20,  zone=BlockDetailviewLocation.RIGHT, model=EmailCampaign)

            BlockDetailviewLocation.create_4_model_block(order=5,   zone=BlockDetailviewLocation.LEFT,  model=EmailTemplate)
            create_bdl(block_id=customfields_block.id_,  order=40,  zone=BlockDetailviewLocation.LEFT,  model=EmailTemplate)
            create_bdl(block_id=attachments_block.id_,   order=60,  zone=BlockDetailviewLocation.LEFT,  model=EmailTemplate)
            create_bdl(block_id=properties_block.id_,    order=450, zone=BlockDetailviewLocation.LEFT,  model=EmailTemplate)
            create_bdl(block_id=relations_block.id_,     order=500, zone=BlockDetailviewLocation.LEFT,  model=EmailTemplate)
            create_bdl(block_id=history_block.id_,       order=20,  zone=BlockDetailviewLocation.RIGHT, model=EmailTemplate)

            #'persons' app
            create_bdl(block_id=mails_history_block.id_, order=600, zone=BlockDetailviewLocation.RIGHT, model=Contact)
            create_bdl(block_id=mails_history_block.id_, order=600, zone=BlockDetailviewLocation.RIGHT, model=Organisation)

            BlockPortalLocation.create(app_name='emails', block_id=signatures_block.id_, order=10)
            BlockPortalLocation.create(app_name='emails', block_id=history_block.id_,    order=30)

            if 'creme.assistants' in settings.INSTALLED_APPS:
                logger.info('Assistants app is installed => we use the assistants blocks on detail views')

                from creme.assistants.blocks import alerts_block, memos_block, todos_block, messages_block

                for model in (MailingList, EmailCampaign, EmailTemplate):
                    create_bdl(block_id=todos_block.id_,    order=100, zone=BlockDetailviewLocation.RIGHT, model=model)
                    create_bdl(block_id=memos_block.id_,    order=200, zone=BlockDetailviewLocation.RIGHT, model=model)
                    create_bdl(block_id=alerts_block.id_,   order=300, zone=BlockDetailviewLocation.RIGHT, model=model)
                    create_bdl(block_id=messages_block.id_, order=400, zone=BlockDetailviewLocation.RIGHT, model=model)

                BlockPortalLocation.create(app_name='emails', block_id=memos_block.id_,    order=100)
                BlockPortalLocation.create(app_name='emails', block_id=alerts_block.id_,   order=200)
                BlockPortalLocation.create(app_name='emails', block_id=messages_block.id_, order=300)


            ButtonMenuItem.create_if_needed(pk='emails-entity_email_link_button', model=EntityEmail, button=entityemail_link_button, order=20)
