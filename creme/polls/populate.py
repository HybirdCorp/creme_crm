# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2012-2018  Hybird
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

from creme.creme_core import bricks as core_bricks
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import HeaderFilter, BrickDetailviewLocation, SearchConfigItem
from creme.creme_core.utils import create_if_needed

from creme import persons

from creme import polls
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

        create_hf = HeaderFilter.create
        create_hf(pk=constants.DEFAULT_HFILTER_PFORM,
                  model=PollForm, name=_(u'Form view'),
                  cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                             ],
                 )
        create_hf(pk=constants.DEFAULT_HFILTER_PREPLY,
                  model=PollReply, name=_(u'Reply view'),
                  cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                              (EntityCellRegularField, {'name': 'pform'}),
                              (EntityCellRegularField, {'name': 'person'}),
                             ],
                 )
        create_hf(pk=constants.DEFAULT_HFILTER_PCAMPAIGN,
                  model=PollCampaign, name=_(u'Campaign view'),
                  cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                              (EntityCellRegularField, {'name': 'due_date'}),
                              (EntityCellRegularField, {'name': 'segment'}),
                             ],
                 )

        # ---------------------------
        create_searchconf = SearchConfigItem.create_if_needed
        create_searchconf(PollForm,     ['name'])
        create_searchconf(PollReply,    ['name'])
        create_searchconf(PollCampaign, ['name'])

        # ---------------------------
        if not PollType.objects.exists():  # NB: no straightforward way to test that this populate script has not been already run
            create_if_needed(PollType, {'pk': 1}, name=_(u'Survey'))
            create_if_needed(PollType, {'pk': 2}, name=_(u'Monitoring'))
            create_if_needed(PollType, {'pk': 3}, name=_(u'Assessment'))

        # ---------------------------
        if not BrickDetailviewLocation.config_exists(PollForm): # NB: no straightforward way to test that this populate script has not been already run
            TOP   = BrickDetailviewLocation.TOP
            LEFT  = BrickDetailviewLocation.LEFT
            RIGHT = BrickDetailviewLocation.RIGHT

            create_bdl = BrickDetailviewLocation.create_if_needed
            create_bdl(brick_id=bricks.PollFormLinesBrick.id_,     order=5,   zone=TOP,   model=PollForm)
            BrickDetailviewLocation.create_4_model_brick(          order=5,   zone=LEFT,  model=PollForm)
            create_bdl(brick_id=core_bricks.CustomFieldsBrick.id_, order=40,  zone=LEFT,  model=PollForm)
            create_bdl(brick_id=core_bricks.PropertiesBrick.id_,   order=450, zone=LEFT,  model=PollForm)
            create_bdl(brick_id=core_bricks.RelationsBrick.id_,    order=500, zone=LEFT,  model=PollForm)
            create_bdl(brick_id=bricks.PollRepliesBrick.id_,       order=5,   zone=RIGHT, model=PollForm)
            create_bdl(brick_id=core_bricks.HistoryBrick.id_,      order=20,  zone=RIGHT, model=PollForm)

            # TODO: factorise
            create_bdl(brick_id=bricks.PollReplyLinesBrick.id_,    order=5,   zone=TOP,   model=PollReply)
            BrickDetailviewLocation.create_4_model_brick(          order=5,   zone=LEFT,  model=PollReply)
            create_bdl(brick_id=core_bricks.CustomFieldsBrick.id_, order=40,  zone=LEFT,  model=PollReply)
            create_bdl(brick_id=core_bricks.PropertiesBrick.id_,   order=450, zone=LEFT,  model=PollReply)
            create_bdl(brick_id=core_bricks.RelationsBrick.id_,    order=500, zone=LEFT,  model=PollReply)
            create_bdl(brick_id=core_bricks.HistoryBrick.id_,      order=20,  zone=RIGHT, model=PollReply)

            BrickDetailviewLocation.create_4_model_brick(            order=5,   zone=LEFT,  model=PollCampaign)
            create_bdl(brick_id=core_bricks.CustomFieldsBrick.id_,   order=40,  zone=LEFT,  model=PollCampaign)
            create_bdl(brick_id=core_bricks.PropertiesBrick.id_,     order=450, zone=LEFT,  model=PollCampaign)
            create_bdl(brick_id=core_bricks.RelationsBrick.id_,      order=500, zone=LEFT,  model=PollCampaign)
            create_bdl(brick_id=bricks.PollCampaignRepliesBrick.id_, order=5,   zone=RIGHT, model=PollCampaign)
            create_bdl(brick_id=core_bricks.HistoryBrick.id_,        order=20,  zone=RIGHT, model=PollCampaign)

            create_bdl(brick_id=bricks.PersonPollRepliesBrick.id_, order=500, zone=RIGHT, model=Contact)
            create_bdl(brick_id=bricks.PersonPollRepliesBrick.id_, order=500, zone=RIGHT, model=Organisation)

            if apps.is_installed('creme.assistants'):
                logger.info('Assistants app is installed => we use the assistants blocks on detail view')

                from creme.assistants import bricks as a_bricks

                for model in (PollForm, PollReply, PollCampaign):
                    create_bdl(brick_id=a_bricks.TodosBrick.id_,        order=100, zone=RIGHT, model=model)
                    create_bdl(brick_id=a_bricks.MemosBrick.id_,        order=200, zone=RIGHT, model=model)
                    create_bdl(brick_id=a_bricks.AlertsBrick.id_,       order=300, zone=RIGHT, model=model)
                    create_bdl(brick_id=a_bricks.UserMessagesBrick.id_, order=400, zone=RIGHT, model=model)

            if apps.is_installed('creme.documents'):
                # logger.info('Documents app is installed => we use the documents block on detail views')

                from creme.documents.bricks import LinkedDocsBrick

                for model in (PollForm, PollReply, PollCampaign):
                    create_bdl(brick_id=LinkedDocsBrick.id_, order=600, zone=RIGHT, model=model)
