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

from creme.creme_core.models import BlockDetailviewLocation, BlockPortalLocation
from creme.creme_core.utils import create_if_needed
from creme.creme_core.management.commands.creme_populate import BasePopulator

from creme.assistants.constants import USERMESSAGE_PRIORITIES
from creme.assistants.models import UserMessagePriority
from creme.assistants.blocks import alerts_block, memos_block, todos_block, messages_block


class Populator(BasePopulator):
    dependencies = ['creme_core']

    def populate(self, *args, **kwargs):
        for pk, title in USERMESSAGE_PRIORITIES.iteritems():
            create_if_needed(UserMessagePriority, {'pk': pk}, title=unicode(title), is_custom=False)

        BlockDetailviewLocation.create(block_id=todos_block.id_,    order=100, zone=BlockDetailviewLocation.RIGHT)
        BlockDetailviewLocation.create(block_id=memos_block.id_,    order=200, zone=BlockDetailviewLocation.RIGHT)
        BlockDetailviewLocation.create(block_id=alerts_block.id_,   order=300, zone=BlockDetailviewLocation.RIGHT)
        BlockDetailviewLocation.create(block_id=messages_block.id_, order=500, zone=BlockDetailviewLocation.RIGHT)

        BlockPortalLocation.create(block_id=memos_block.id_,    order=100)
        BlockPortalLocation.create(block_id=alerts_block.id_,   order=200)
        BlockPortalLocation.create(block_id=messages_block.id_, order=400)

        BlockPortalLocation.create(app_name='creme_core', block_id=memos_block.id_,    order=100)
        BlockPortalLocation.create(app_name='creme_core', block_id=alerts_block.id_,   order=200)
        BlockPortalLocation.create(app_name='creme_core', block_id=messages_block.id_, order=400)

        BlockPortalLocation.create(block_id=memos_block.id_,    order=100)
        BlockPortalLocation.create(block_id=alerts_block.id_,   order=200)
        BlockPortalLocation.create(block_id=messages_block.id_, order=400)
