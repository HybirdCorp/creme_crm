# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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
from creme.creme_core.gui.custom_form import EntityCellCustomFormSpecial
from creme.creme_core.gui.menu import ContainerEntry
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (
    BrickDetailviewLocation,
    CustomFormConfigItem,
    HeaderFilter,
    MenuConfigItem,
    SearchConfigItem,
)

from . import bricks, custom_forms, get_graph_model
from .constants import DEFAULT_HFILTER_GRAPH
from .menu import GraphsEntry

logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core']

    def populate(self):
        Graph = get_graph_model()

        HeaderFilter.objects.create_if_needed(
            pk=DEFAULT_HFILTER_GRAPH, name=_('Graph view'), model=Graph,
            cells_desc=[(EntityCellRegularField, {'name': 'name'})],
        )

        # ---------------------------
        base_groups_desc = [
            {
                'name': _('General information'),
                'cells': [
                    (EntityCellRegularField, {'name': 'user'}),
                    (EntityCellRegularField, {'name': 'name'}),
                    (
                        EntityCellCustomFormSpecial,
                        {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                    ),
                ],
            }, {
                'name': _('Description'),
                'cells': [
                    (EntityCellRegularField, {'name': 'description'}),
                ],
            }, {
                'name': _('Custom fields'),
                'cells': [
                    (
                        EntityCellCustomFormSpecial,
                        {'name': EntityCellCustomFormSpecial.REMAINING_CUSTOMFIELDS},
                    ),
                ],
            },
        ]

        CustomFormConfigItem.objects.create_if_needed(
            descriptor=custom_forms.GRAPH_CREATION_CFORM,
            groups_desc=[
                *base_groups_desc,
                {
                    'name': _('Properties'),
                    'cells': [
                        (
                            EntityCellCustomFormSpecial,
                            {'name': EntityCellCustomFormSpecial.CREME_PROPERTIES},
                        ),
                    ],
                }, {
                    'name': _('Relationships'),
                    'cells': [
                        (
                            EntityCellCustomFormSpecial,
                            {'name': EntityCellCustomFormSpecial.RELATIONS},
                        ),
                    ],
                },
            ],
        )
        CustomFormConfigItem.objects.create_if_needed(
            descriptor=custom_forms.GRAPH_EDITION_CFORM,
            groups_desc=base_groups_desc,
        )

        # ---------------------------
        SearchConfigItem.objects.create_if_needed(Graph, ['name'])

        # ---------------------------
        # TODO: move to "not already_populated" section in creme2.4
        if not MenuConfigItem.objects.filter(entry_id__startswith='graphs-').exists():
            container = MenuConfigItem.objects.get_or_create(
                entry_id=ContainerEntry.id,
                entry_data={'label': _('Analysis')},
                defaults={'order': 500},
            )[0]

            MenuConfigItem.objects.create(
                entry_id=GraphsEntry.id, parent=container, order=50,
            )

        # ---------------------------
        # NB: no straightforward way to test that this populate script has not been already run
        if not BrickDetailviewLocation.objects.filter_for_model(Graph).exists():
            RIGHT = BrickDetailviewLocation.RIGHT

            BrickDetailviewLocation.objects.multi_create(
                defaults={'model': Graph, 'zone': BrickDetailviewLocation.LEFT},
                data=[
                    {'order': 5},
                    {'brick': core_bricks.CustomFieldsBrick,    'order':  40},
                    {'brick': bricks.RootNodesBrick,            'order':  60},
                    {'brick': bricks.OrbitalRelationTypesBrick, 'order':  65},
                    {'brick': core_bricks.PropertiesBrick,      'order': 450},
                    {'brick': core_bricks.RelationsBrick,       'order': 500},

                    {'brick': core_bricks.HistoryBrick, 'order': 20, 'zone': RIGHT},
                ],
            )

            if apps.is_installed('creme.assistants'):
                logger.info(
                    'Assistants app is installed'
                    ' => we use the assistants blocks on detail view'
                )

                from creme.assistants import bricks as a_bricks

                BrickDetailviewLocation.objects.multi_create(
                    defaults={'model': Graph, 'zone': RIGHT},
                    data=[
                        {'brick': a_bricks.TodosBrick,        'order': 100},
                        {'brick': a_bricks.MemosBrick,        'order': 200},
                        {'brick': a_bricks.AlertsBrick,       'order': 300},
                        {'brick': a_bricks.UserMessagesBrick, 'order': 400},
                    ],
                )

            if apps.is_installed('creme.documents'):
                # logger.info('Documents app is installed
                # => we use the documents blocks on detail view')

                from creme.documents.bricks import LinkedDocsBrick

                BrickDetailviewLocation.objects.create_if_needed(
                    brick=LinkedDocsBrick, order=600, zone=RIGHT, model=Graph,
                )
