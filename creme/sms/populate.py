# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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

from django.apps import apps
from django.utils.translation import ugettext as _

from creme.creme_core.blocks import (properties_block, relations_block,
        customfields_block, history_block)
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import SearchConfigItem, HeaderFilter, BlockDetailviewLocation

from . import get_smscampaign_model, get_messaginglist_model, get_messagetemplate_model
from . import constants
from .blocks import messaging_lists_block, recipients_block, contacts_block, sendings_block


logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core']

    def populate(self):
        SMSCampaign     = get_smscampaign_model()
        MessagingList   = get_messaginglist_model()
        MessageTemplate = get_messagetemplate_model()

        create_hf = HeaderFilter.create
        create_hf(pk=constants.DEFAULT_HFILTER_MLIST,
                  model=MessagingList,
                  name=_(u'Messaging list view'),
                  cells_desc=[(EntityCellRegularField, {'name': 'name'})],
                 )
        create_hf(pk=constants.DEFAULT_HFILTER_SMSCAMPAIGN,
                  model=SMSCampaign,
                  name=_(u'Campaign view'),
                  cells_desc=[(EntityCellRegularField, {'name': 'name'})],
                 )
        create_hf(pk=constants.DEFAULT_HFILTER_MTEMPLATE,
                  model=MessageTemplate,
                  name=_(u'Message template view'),
                  cells_desc=[(EntityCellRegularField, {'name': 'name'})],
                 )

        # ---------------------------
        create_searchconf = SearchConfigItem.create_if_needed
        create_searchconf(SMSCampaign, ['name'])
        create_searchconf(MessagingList, ['name'])
        create_searchconf(MessageTemplate, ['name', 'subject', 'body'])

        # ---------------------------
        if not BlockDetailviewLocation.config_exists(SMSCampaign): # NB: no straightforward way to test that this populate script has not been already run
            create_bdl = BlockDetailviewLocation.create
            TOP   = BlockDetailviewLocation.TOP
            LEFT  = BlockDetailviewLocation.LEFT
            RIGHT = BlockDetailviewLocation.RIGHT

            BlockDetailviewLocation.create_4_model_block(order=5,     zone=LEFT,  model=SMSCampaign)
            create_bdl(block_id=sendings_block.id_,        order=2,   zone=TOP,   model=SMSCampaign)
            create_bdl(block_id=customfields_block.id_,    order=40,  zone=LEFT,  model=SMSCampaign)
            create_bdl(block_id=messaging_lists_block.id_, order=50,  zone=LEFT,  model=SMSCampaign)
            create_bdl(block_id=properties_block.id_,      order=450, zone=LEFT,  model=SMSCampaign)
            create_bdl(block_id=relations_block.id_,       order=500, zone=LEFT,  model=SMSCampaign)
            create_bdl(block_id=history_block.id_,         order=20,  zone=RIGHT, model=SMSCampaign)

            BlockDetailviewLocation.create_4_model_block(order=5,   zone=LEFT,  model=MessagingList)
            create_bdl(block_id=customfields_block.id_,  order=40,  zone=LEFT,  model=MessagingList)
            create_bdl(block_id=recipients_block.id_,    order=50,  zone=LEFT,  model=MessagingList)
            create_bdl(block_id=contacts_block.id_,      order=55,  zone=LEFT,  model=MessagingList)
            create_bdl(block_id=properties_block.id_,    order=450, zone=LEFT,  model=MessagingList)
            create_bdl(block_id=relations_block.id_,     order=500, zone=LEFT,  model=MessagingList)
            create_bdl(block_id=history_block.id_,       order=20,  zone=RIGHT, model=MessagingList)

            if apps.is_installed('creme.assistants'):
                logger.info('Assistants app is installed => we use the assistants blocks on detail views')

                from creme.assistants.blocks import alerts_block, memos_block, todos_block, messages_block

                for model in (SMSCampaign, MessagingList):
                    create_bdl(block_id=todos_block.id_,    order=100, zone=RIGHT, model=model)
                    create_bdl(block_id=memos_block.id_,    order=200, zone=RIGHT, model=model)
                    create_bdl(block_id=alerts_block.id_,   order=300, zone=RIGHT, model=model)
                    create_bdl(block_id=messages_block.id_, order=400, zone=RIGHT, model=model)

            if apps.is_installed('creme.documents'):
                # logger.info("Documents app is installed => we use the documents block on SMSCampaign's detail views")

                from creme.documents.blocks import linked_docs_block

                create_bdl(block_id=linked_docs_block.id_, order=600, zone=RIGHT, model=SMSCampaign)
