# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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
from django.utils.translation import gettext as _

from creme.creme_core import bricks as core_bricks
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import SearchConfigItem, HeaderFilter, BrickDetailviewLocation

from creme import sms
from . import bricks, constants

logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core']

    def populate(self):
        SMSCampaign     = sms.get_smscampaign_model()
        MessagingList   = sms.get_messaginglist_model()
        MessageTemplate = sms.get_messagetemplate_model()

        create_hf = HeaderFilter.create
        create_hf(pk=constants.DEFAULT_HFILTER_MLIST,
                  model=MessagingList,
                  name=_('Messaging list view'),
                  cells_desc=[(EntityCellRegularField, {'name': 'name'})],
                 )
        create_hf(pk=constants.DEFAULT_HFILTER_SMSCAMPAIGN,
                  model=SMSCampaign,
                  name=_('Campaign view'),
                  cells_desc=[(EntityCellRegularField, {'name': 'name'})],
                 )
        create_hf(pk=constants.DEFAULT_HFILTER_MTEMPLATE,
                  model=MessageTemplate,
                  name=_('Message template view'),
                  cells_desc=[(EntityCellRegularField, {'name': 'name'})],
                 )

        # ---------------------------
        create_searchconf = SearchConfigItem.create_if_needed
        create_searchconf(SMSCampaign, ['name'])
        create_searchconf(MessagingList, ['name'])
        create_searchconf(MessageTemplate, ['name', 'subject', 'body'])

        # ---------------------------
        if not BrickDetailviewLocation.config_exists(SMSCampaign): # NB: no straightforward way to test that this populate script has not been already run
            create_bdl = BrickDetailviewLocation.create_if_needed
            TOP   = BrickDetailviewLocation.TOP
            LEFT  = BrickDetailviewLocation.LEFT
            RIGHT = BrickDetailviewLocation.RIGHT

            BrickDetailviewLocation.create_4_model_brick(          order=5,   zone=LEFT,  model=SMSCampaign)
            create_bdl(brick_id=bricks.SendingsBrick.id_,          order=2,   zone=TOP,   model=SMSCampaign)
            create_bdl(brick_id=core_bricks.CustomFieldsBrick.id_, order=40,  zone=LEFT,  model=SMSCampaign)
            create_bdl(brick_id=bricks.MessagingListsBlock.id_,    order=50,  zone=LEFT,  model=SMSCampaign)
            create_bdl(brick_id=core_bricks.PropertiesBrick.id_,   order=450, zone=LEFT,  model=SMSCampaign)
            create_bdl(brick_id=core_bricks.RelationsBrick.id_,    order=500, zone=LEFT,  model=SMSCampaign)
            create_bdl(brick_id=core_bricks.HistoryBrick.id_,      order=20,  zone=RIGHT, model=SMSCampaign)

            BrickDetailviewLocation.create_4_model_brick(          order=5,   zone=LEFT,  model=MessagingList)
            create_bdl(brick_id=core_bricks.CustomFieldsBrick.id_, order=40,  zone=LEFT,  model=MessagingList)
            create_bdl(brick_id=bricks.RecipientsBrick.id_,        order=50,  zone=LEFT,  model=MessagingList)
            create_bdl(brick_id=bricks.ContactsBrick.id_,          order=55,  zone=LEFT,  model=MessagingList)
            create_bdl(brick_id=core_bricks.PropertiesBrick.id_,   order=450, zone=LEFT,  model=MessagingList)
            create_bdl(brick_id=core_bricks.RelationsBrick.id_,    order=500, zone=LEFT,  model=MessagingList)
            create_bdl(brick_id=core_bricks.HistoryBrick.id_,      order=20,  zone=RIGHT, model=MessagingList)

            if apps.is_installed('creme.assistants'):
                logger.info('Assistants app is installed => we use the assistants blocks on detail views')

                from creme.assistants import bricks as a_bricks

                for model in (SMSCampaign, MessagingList):
                    create_bdl(brick_id=a_bricks.TodosBrick.id_,        order=100, zone=RIGHT, model=model)
                    create_bdl(brick_id=a_bricks.MemosBrick.id_,        order=200, zone=RIGHT, model=model)
                    create_bdl(brick_id=a_bricks.AlertsBrick.id_,       order=300, zone=RIGHT, model=model)
                    create_bdl(brick_id=a_bricks.UserMessagesBrick.id_, order=400, zone=RIGHT, model=model)

            if apps.is_installed('creme.documents'):
                # logger.info("Documents app is installed => we use the documents block on SMSCampaign's detail views")

                from creme.documents.bricks import LinkedDocsBrick

                create_bdl(brick_id=LinkedDocsBrick.id_, order=600, zone=RIGHT, model=SMSCampaign)
