# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from creme_core.models import BlockConfigItem
from creme_core.utils import create_or_update_models_instance as create
from creme_core.management.commands.creme_populate import BasePopulator

from blocks import alerts_block, actions_it_block, actions_nit_block, memos_block, todos_block


class Populator(BasePopulator):
    dependencies = ['creme.creme_core']

    def populate(self, *args, **kwargs):
        create(BlockConfigItem, 'assistants-todos_block',       content_type=None, block_id=todos_block.id_,       order=100, on_portal=False)
        create(BlockConfigItem, 'assistants-memos_block',       content_type=None, block_id=memos_block.id_,       order=200, on_portal=True)
        create(BlockConfigItem, 'assistants-alerts_block',      content_type=None, block_id=alerts_block.id_,      order=300, on_portal=True)
        create(BlockConfigItem, 'assistants-actions_it_block',  content_type=None, block_id=actions_it_block.id_,  order=400, on_portal=True)
        create(BlockConfigItem, 'assistants-actions_nit_block', content_type=None, block_id=actions_nit_block.id_, order=410, on_portal=True)
