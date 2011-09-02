# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from logging import info

from django.utils.translation import ugettext as _
from django.conf import settings

from creme_core.models import SearchConfigItem, HeaderFilterItem, HeaderFilter, BlockDetailviewLocation
from creme_core.blocks import properties_block, relations_block, customfields_block, history_block
from creme_core.management.commands.creme_populate import BasePopulator

from reports.models import Report
from reports.blocks import report_fields_block, report_graphs_block


class Populator(BasePopulator):
    dependencies = ['creme.creme_core']

    def populate(self, *args, **kwargs):
        hf = HeaderFilter.create(pk='reports-hf', name=_(u'Report view'), model=Report)
        hf.set_items([HeaderFilterItem.build_4_field(model=Report, name='name'),
                      HeaderFilterItem.build_4_field(model=Report, name='ct__name'),
                     ])

        BlockDetailviewLocation.create(block_id=customfields_block.id_,  order=40,  zone=BlockDetailviewLocation.LEFT,  model=Report)
        BlockDetailviewLocation.create(block_id=report_fields_block.id_, order=50,  zone=BlockDetailviewLocation.LEFT,  model=Report)
        BlockDetailviewLocation.create(block_id=report_graphs_block.id_, order=60,  zone=BlockDetailviewLocation.LEFT,  model=Report)
        BlockDetailviewLocation.create(block_id=properties_block.id_,    order=450, zone=BlockDetailviewLocation.LEFT,  model=Report)
        BlockDetailviewLocation.create(block_id=relations_block.id_,     order=500, zone=BlockDetailviewLocation.LEFT,  model=Report)
        BlockDetailviewLocation.create(block_id=history_block.id_,       order=20,  zone=BlockDetailviewLocation.RIGHT, model=Report)

        if 'creme.assistants' in settings.INSTALLED_APPS:
            info('Assistants app is installed => we use the assistants blocks on detail view')

            from assistants.blocks import alerts_block, memos_block, todos_block, messages_block

            BlockDetailviewLocation.create(block_id=todos_block.id_,    order=100, zone=BlockDetailviewLocation.RIGHT, model=Report)
            BlockDetailviewLocation.create(block_id=memos_block.id_,    order=200, zone=BlockDetailviewLocation.RIGHT, model=Report)
            BlockDetailviewLocation.create(block_id=alerts_block.id_,   order=300, zone=BlockDetailviewLocation.RIGHT, model=Report)
            BlockDetailviewLocation.create(block_id=messages_block.id_, order=400, zone=BlockDetailviewLocation.RIGHT, model=Report)

        SearchConfigItem.create(Report, ['name', 'ct__name'])
