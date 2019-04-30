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

from . import get_report_model, bricks, constants

logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core']

    def populate(self):
        Report = get_report_model()

        HeaderFilter.create(pk=constants.DEFAULT_HFILTER_REPORT,
                            name=_('Report view'), model=Report,
                            cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                                        (EntityCellRegularField, {'name': 'ct'}),
                                       ],
                           )

        # ---------------------------
        SearchConfigItem.create_if_needed(Report, ['name'])

        # ---------------------------
        if not BrickDetailviewLocation.config_exists(Report):  # NB: no straightforward way to test that this populate script has not been already run
            create_bdl = BrickDetailviewLocation.create_if_needed
            LEFT  = BrickDetailviewLocation.LEFT
            RIGHT = BrickDetailviewLocation.RIGHT

            BrickDetailviewLocation.create_4_model_brick(order=5, zone=LEFT, model=Report)
            create_bdl(brick_id=core_bricks.CustomFieldsBrick.id_, order=40,  zone=LEFT,  model=Report)
            create_bdl(brick_id=bricks.ReportFieldsBrick.id_,      order=50,  zone=LEFT,  model=Report)
            create_bdl(brick_id=bricks.ReportGraphsBrick.id_,      order=60,  zone=LEFT,  model=Report)
            create_bdl(brick_id=core_bricks.PropertiesBrick.id_,   order=450, zone=LEFT,  model=Report)
            create_bdl(brick_id=core_bricks.RelationsBrick.id_,    order=500, zone=LEFT,  model=Report)
            create_bdl(brick_id=core_bricks.HistoryBrick.id_,      order=20,  zone=RIGHT, model=Report)

            if apps.is_installed('creme.assistants'):
                logger.info('Assistants app is installed => we use the assistants blocks on detail view')

                from creme.assistants import bricks as a_bricks

                create_bdl(brick_id=a_bricks.TodosBrick.id_,        order=100, zone=RIGHT, model=Report)
                create_bdl(brick_id=a_bricks.MemosBrick.id_,        order=200, zone=RIGHT, model=Report)
                create_bdl(brick_id=a_bricks.AlertsBrick.id_,       order=300, zone=RIGHT, model=Report)
                create_bdl(brick_id=a_bricks.UserMessagesBrick.id_, order=400, zone=RIGHT, model=Report)

            if apps.is_installed('creme.documents'):
                # logger.info('Documents app is installed => we use the documents block on detail views')

                from creme.documents.bricks import LinkedDocsBrick

                create_bdl(brick_id=LinkedDocsBrick.id_, order=600, zone=RIGHT, model=Report)
