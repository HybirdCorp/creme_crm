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

from creme.creme_core import bricks as core_bricks
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (
    BrickDetailviewLocation,
    HeaderFilter,
    SearchConfigItem,
)

from . import bricks, constants, get_report_model

logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core']

    def populate(self):
        Report = get_report_model()

        HeaderFilter.objects.create_if_needed(
            pk=constants.DEFAULT_HFILTER_REPORT,
            name=_('Report view'), model=Report,
            cells_desc=[
                (EntityCellRegularField, {'name': 'name'}),
                (EntityCellRegularField, {'name': 'ct'}),
            ],
        )

        # ---------------------------
        SearchConfigItem.objects.create_if_needed(Report, ['name'])

        # ---------------------------
        # NB: no straightforward way to test that this populate script has not been already run
        if not BrickDetailviewLocation.objects.filter_for_model(Report).exists():
            RIGHT = BrickDetailviewLocation.RIGHT

            BrickDetailviewLocation.objects.multi_create(
                defaults={'model': Report, 'zone': BrickDetailviewLocation.LEFT},
                data=[
                    {'order': 5},
                    {'brick': core_bricks.CustomFieldsBrick, 'order':  40},
                    {'brick': bricks.ReportFieldsBrick,      'order':  50},
                    {'brick': bricks.ReportGraphsBrick,      'order':  60},
                    {'brick': core_bricks.PropertiesBrick,   'order': 450},
                    {'brick': core_bricks.RelationsBrick,    'order': 500},

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
                    defaults={'model': Report, 'zone': RIGHT},
                    data=[
                        {'brick': a_bricks.TodosBrick,        'order': 100},
                        {'brick': a_bricks.MemosBrick,        'order': 200},
                        {'brick': a_bricks.AlertsBrick,       'order': 300},
                        {'brick': a_bricks.UserMessagesBrick, 'order': 400},
                    ],
                )

            if apps.is_installed('creme.documents'):
                # logger.info('Documents app is installed
                # => we use the documents block on detail views')

                from creme.documents.bricks import LinkedDocsBrick

                BrickDetailviewLocation.objects.create_if_needed(
                    brick=LinkedDocsBrick, order=600, zone=RIGHT, model=Report,
                )
