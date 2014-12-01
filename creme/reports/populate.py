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

from creme.creme_core.blocks import properties_block, relations_block, customfields_block, history_block
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import SearchConfigItem, HeaderFilter, BlockDetailviewLocation

from .blocks import report_fields_block, report_graphs_block
from .models import Report


logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core']

    def populate(self):
        HeaderFilter.create(pk='reports-hf', name=_(u'Report view'), model=Report,
                            cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                                        (EntityCellRegularField, {'name': 'ct'}),
                                       ],
                           )


        SearchConfigItem.create_if_needed(Report, ['name', 'ct__name'])


        if not BlockDetailviewLocation.config_exists(Report): # NB: no straightforward way to test that this populate script has not been already runned
            create_bdl = BlockDetailviewLocation.create
            BlockDetailviewLocation.create_4_model_block(order=5,   zone=BlockDetailviewLocation.LEFT,  model=Report)
            create_bdl(block_id=customfields_block.id_,  order=40,  zone=BlockDetailviewLocation.LEFT,  model=Report)
            create_bdl(block_id=report_fields_block.id_, order=50,  zone=BlockDetailviewLocation.LEFT,  model=Report)
            create_bdl(block_id=report_graphs_block.id_, order=60,  zone=BlockDetailviewLocation.LEFT,  model=Report)
            create_bdl(block_id=properties_block.id_,    order=450, zone=BlockDetailviewLocation.LEFT,  model=Report)
            create_bdl(block_id=relations_block.id_,     order=500, zone=BlockDetailviewLocation.LEFT,  model=Report)
            create_bdl(block_id=history_block.id_,       order=20,  zone=BlockDetailviewLocation.RIGHT, model=Report)


            if 'creme.assistants' in settings.INSTALLED_APPS:
                logger.info('Assistants app is installed => we use the assistants blocks on detail view')

                from creme.assistants.blocks import alerts_block, memos_block, todos_block, messages_block

                create_bdl(block_id=todos_block.id_,    order=100, zone=BlockDetailviewLocation.RIGHT, model=Report)
                create_bdl(block_id=memos_block.id_,    order=200, zone=BlockDetailviewLocation.RIGHT, model=Report)
                create_bdl(block_id=alerts_block.id_,   order=300, zone=BlockDetailviewLocation.RIGHT, model=Report)
                create_bdl(block_id=messages_block.id_, order=400, zone=BlockDetailviewLocation.RIGHT, model=Report)
