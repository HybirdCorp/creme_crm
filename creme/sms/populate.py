# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

from creme import sms
from creme.creme_core import bricks as core_bricks
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (
    BrickDetailviewLocation,
    HeaderFilter,
    SearchConfigItem,
)

from . import bricks, constants

logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core']

    def populate(self):
        SMSCampaign     = sms.get_smscampaign_model()
        MessagingList   = sms.get_messaginglist_model()
        MessageTemplate = sms.get_messagetemplate_model()

        create_hf = HeaderFilter.objects.create_if_needed
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
        create_searchconf = SearchConfigItem.objects.create_if_needed
        create_searchconf(SMSCampaign, ['name'])
        create_searchconf(MessagingList, ['name'])
        create_searchconf(MessageTemplate, ['name', 'subject', 'body'])

        # ---------------------------
        # NB: no straightforward way to test that this populate script has not been already run
        if not BrickDetailviewLocation.objects.filter_for_model(SMSCampaign).exists():
            create_bdl         = BrickDetailviewLocation.objects.create_if_needed
            create_bdl_4_model = BrickDetailviewLocation.objects.create_for_model_brick

            TOP   = BrickDetailviewLocation.TOP
            LEFT  = BrickDetailviewLocation.LEFT
            RIGHT = BrickDetailviewLocation.RIGHT

            def create_multi_bdl(model, info):
                for brick, order, zone in info:
                    if brick == 'model':
                        create_bdl_4_model(order=order, zone=zone, model=model)
                    else:
                        create_bdl(brick=brick, order=order, zone=zone, model=model)

            create_multi_bdl(
                SMSCampaign,
                [
                    (bricks.SendingsBrick,           2,  TOP),
                    ('model',                        5,  LEFT),
                    (core_bricks.CustomFieldsBrick, 40,  LEFT),
                    (bricks.MessagingListsBlock,    50,  LEFT),
                    (core_bricks.PropertiesBrick,   450, LEFT),
                    (core_bricks.RelationsBrick,    500, LEFT),
                    (core_bricks.HistoryBrick,      20,  RIGHT),
                ],
            )
            create_multi_bdl(
                MessagingList,
                [
                    ('model',                         5, LEFT),
                    (core_bricks.CustomFieldsBrick,  40, LEFT),
                    (bricks.RecipientsBrick,         50, LEFT),
                    (bricks.ContactsBrick,           55, LEFT),
                    (core_bricks.PropertiesBrick,   450, LEFT),
                    (core_bricks.RelationsBrick,    500, LEFT),
                    (core_bricks.HistoryBrick,       20, RIGHT),
                ],
            )

            if apps.is_installed('creme.assistants'):
                logger.info(
                    'Assistants app is installed => we use the assistants blocks on detail views'
                )

                from creme.assistants import bricks as a_bricks

                for model in (SMSCampaign, MessagingList):
                    create_multi_bdl(
                        model,
                        [
                            (a_bricks.TodosBrick,        100, RIGHT),
                            (a_bricks.MemosBrick,        200, RIGHT),
                            (a_bricks.AlertsBrick,       300, RIGHT),
                            (a_bricks.UserMessagesBrick, 400, RIGHT),
                        ]
                    )

            if apps.is_installed('creme.documents'):
                # logger.info("Documents app is installed =>
                # we use the documents block on SMSCampaign's detail views")

                from creme.documents.bricks import LinkedDocsBrick

                create_bdl(brick=LinkedDocsBrick, order=600, zone=RIGHT, model=SMSCampaign)
