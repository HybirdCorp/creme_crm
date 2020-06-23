# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2012-2020  Hybird
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

from creme import persons, polls
from creme.creme_core import bricks as core_bricks
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (
    BrickDetailviewLocation,
    HeaderFilter,
    SearchConfigItem,
)
from creme.creme_core.utils import create_if_needed

from . import bricks, constants
from .models import PollType

logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core', 'persons']

    def populate(self, *args, **kwargs):
        PollCampaign = polls.get_pollcampaign_model()
        PollForm     = polls.get_pollform_model()
        PollReply    = polls.get_pollreply_model()

        Contact      = persons.get_contact_model()
        Organisation = persons.get_organisation_model()

        create_hf = HeaderFilter.objects.create_if_needed
        create_hf(pk=constants.DEFAULT_HFILTER_PFORM,
                  model=PollForm, name=_('Form view'),
                  cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                              ],
                  )
        create_hf(pk=constants.DEFAULT_HFILTER_PREPLY,
                  model=PollReply, name=_('Reply view'),
                  cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                              (EntityCellRegularField, {'name': 'pform'}),
                              (EntityCellRegularField, {'name': 'person'}),
                              ],
                  )
        create_hf(pk=constants.DEFAULT_HFILTER_PCAMPAIGN,
                  model=PollCampaign, name=_('Campaign view'),
                  cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                              (EntityCellRegularField, {'name': 'due_date'}),
                              (EntityCellRegularField, {'name': 'segment'}),
                              ],
                  )

        # ---------------------------
        create_searchconf = SearchConfigItem.objects.create_if_needed
        create_searchconf(PollForm,     ['name'])
        create_searchconf(PollReply,    ['name'])
        create_searchconf(PollCampaign, ['name'])

        # ---------------------------
        # NB: no straightforward way to test that this populate script has not been already run
        if not PollType.objects.exists():
            create_if_needed(PollType, {'pk': 1}, name=_('Survey'))
            create_if_needed(PollType, {'pk': 2}, name=_('Monitoring'))
            create_if_needed(PollType, {'pk': 3}, name=_('Assessment'))

        # ---------------------------
        # NB: no straightforward way to test that this populate script has not been already run
        if not BrickDetailviewLocation.objects.filter_for_model(PollForm).exists():
            TOP   = BrickDetailviewLocation.TOP
            LEFT  = BrickDetailviewLocation.LEFT
            RIGHT = BrickDetailviewLocation.RIGHT

            create_bdl         = BrickDetailviewLocation.objects.create_if_needed
            create_bdl_4_model = BrickDetailviewLocation.objects.create_for_model_brick

            def create_multi_bdl(model, info):
                for brick, order, zone in info:
                    if brick == 'model':
                        create_bdl_4_model(order=order, zone=zone, model=model)
                    else:
                        create_bdl(brick=brick, order=order, zone=zone, model=model)

            create_multi_bdl(
                PollForm,
                [
                    (bricks.PollFormLinesBrick,       5, TOP),
                    ('model',                         5, LEFT),
                    (core_bricks.CustomFieldsBrick,  40, LEFT),
                    (core_bricks.PropertiesBrick,   450, LEFT),
                    (core_bricks.RelationsBrick,    500, LEFT),
                    (bricks.PollRepliesBrick,         5, RIGHT),
                    (core_bricks.HistoryBrick,       20, RIGHT),
                ]
            )
            create_multi_bdl(
                PollReply,
                [
                    (bricks.PollReplyLinesBrick,    5,   TOP),
                    ('model',                       5,   LEFT),
                    (core_bricks.CustomFieldsBrick, 40,  LEFT),
                    (core_bricks.PropertiesBrick,   450, LEFT),
                    (core_bricks.RelationsBrick,    500, LEFT),
                    (core_bricks.HistoryBrick,      20,  RIGHT),
                ]
            )
            create_multi_bdl(
                PollCampaign,
                [
                    ('model',                         5,   LEFT),
                    (core_bricks.CustomFieldsBrick,   40,  LEFT),
                    (core_bricks.PropertiesBrick,     450, LEFT),
                    (core_bricks.RelationsBrick,      500, LEFT),
                    (bricks.PollCampaignRepliesBrick, 5,   RIGHT),
                    (core_bricks.HistoryBrick,        20,  RIGHT),
                ]
            )

            create_bdl(
                brick=bricks.PersonPollRepliesBrick, order=500, zone=RIGHT, model=Contact,
            )
            create_bdl(
                brick=bricks.PersonPollRepliesBrick, order=500, zone=RIGHT, model=Organisation,
            )

            if apps.is_installed('creme.assistants'):
                logger.info(
                    'Assistants app is installed'
                    ' => we use the assistants blocks on detail view'
                )

                from creme.assistants.bricks import (
                    AlertsBrick,
                    MemosBrick,
                    TodosBrick,
                    UserMessagesBrick,
                )

                for model in (PollForm, PollReply, PollCampaign):
                    create_bdl(brick=TodosBrick,        order=100, zone=RIGHT, model=model)
                    create_bdl(brick=MemosBrick,        order=200, zone=RIGHT, model=model)
                    create_bdl(brick=AlertsBrick,       order=300, zone=RIGHT, model=model)
                    create_bdl(brick=UserMessagesBrick, order=400, zone=RIGHT, model=model)

            if apps.is_installed('creme.documents'):
                # logger.info('Documents app is installed
                # => we use the documents block on detail views')

                from creme.documents.bricks import LinkedDocsBrick

                for model in (PollForm, PollReply, PollCampaign):
                    create_bdl(brick=LinkedDocsBrick, order=600, zone=RIGHT, model=model)
