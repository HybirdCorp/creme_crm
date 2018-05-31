# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2017  Hybird
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
from creme.creme_core.models import SearchConfigItem, HeaderFilter, BrickDetailviewLocation
from creme.creme_core.management.commands.creme_populate import BasePopulator

from . import get_graph_model, bricks
from .constants import DEFAULT_HFILTER_GRAPH


logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core']

    def populate(self):
        Graph = get_graph_model()

        HeaderFilter.create(pk=DEFAULT_HFILTER_GRAPH, name=_(u'Graph view'), model=Graph,
                            cells_desc=[(EntityCellRegularField, {'name': 'name'})],
                           )

        SearchConfigItem.create_if_needed(Graph, ['name'])

        if not BrickDetailviewLocation.config_exists(Graph):  # NB: no straightforward way to test that this populate script has not been already run
            create_bdl = BrickDetailviewLocation.create_if_needed
            LEFT  = BrickDetailviewLocation.LEFT
            RIGHT = BrickDetailviewLocation.RIGHT

            BrickDetailviewLocation.create_4_model_brick(             order=5,   zone=LEFT,  model=Graph)
            create_bdl(brick_id=core_bricks.CustomFieldsBrick.id_,    order=40,  zone=LEFT,  model=Graph)
            create_bdl(brick_id=bricks.RootNodesBrick.id_,            order=60,  zone=LEFT,  model=Graph)
            create_bdl(brick_id=bricks.OrbitalRelationTypesBrick.id_, order=65,  zone=LEFT,  model=Graph)
            create_bdl(brick_id=core_bricks.PropertiesBrick.id_,      order=450, zone=LEFT,  model=Graph)
            create_bdl(brick_id=core_bricks.RelationsBrick.id_,       order=500, zone=LEFT,  model=Graph)
            create_bdl(brick_id=core_bricks.HistoryBrick.id_,         order=20,  zone=RIGHT, model=Graph)

            if apps.is_installed('creme.assistants'):
                logger.info('Assistants app is installed => we use the assistants blocks on detail view')

                from creme.assistants import bricks as a_bricks

                create_bdl(brick_id=a_bricks.TodosBrick.id_,        order=100, zone=RIGHT, model=Graph)
                create_bdl(brick_id=a_bricks.MemosBrick.id_,        order=200, zone=RIGHT, model=Graph)
                create_bdl(brick_id=a_bricks.AlertsBrick.id_,       order=300, zone=RIGHT, model=Graph)
                create_bdl(brick_id=a_bricks.UserMessagesBrick.id_, order=400, zone=RIGHT, model=Graph)

            if apps.is_installed('creme.documents'):
                # logger.info('Documents app is installed => we use the documents blocks on detail view')

                from creme.documents.bricks import LinkedDocsBrick

                create_bdl(brick_id=LinkedDocsBrick.id_, order=600, zone=RIGHT, model=Graph)
