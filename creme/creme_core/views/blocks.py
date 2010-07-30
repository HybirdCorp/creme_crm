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

from datetime import datetime

from django.template import RequestContext
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required

from creme_core.models import CremeEntity
from creme_core.entities_access.functions_for_permissions import read_object_or_die
from creme_core.gui.block import block_registry, str2list, BlocksManager
from creme_core.utils import jsonify

#TODO: credentials..... (+ @get_view_or_die('app_name'))

def _get_depblock_ids(request, block_id):
    ids = [block_id]

    posted_deps  = request.GET.get(block_id + '_deps')
    if posted_deps:
        ids.extend(posted_deps.split(','))

    return ids

@login_required
@jsonify
def reload_detailview(request, block_id, entity_id):
    entity = get_object_or_404(CremeEntity, pk=entity_id).get_real_entity() #get_real_entity() ??

    die_status = read_object_or_die(request, entity)
    if die_status:
        return die_status

    context = RequestContext(request)
    context['object'] = entity
    blocks_manager = BlocksManager.get(context)
    blocks = []

    for block_id in _get_depblock_ids(request, block_id):
        block = block_registry[block_id]
        blocks_manager.add_group(block_id, block)
        blocks.append((block_id, block.detailview_display(context)))

    return blocks

@login_required
@jsonify
def reload_home(request, block_id):
    context = RequestContext(request)
    blocks_manager = BlocksManager.get(context)
    depblock_ids = _get_depblock_ids(request, block_id)
    blocks = []

    for block_id in depblock_ids:
        block = block_registry[block_id]
        blocks_manager.add_group(block_id, block)
        blocks.append((block_id, block.home_display(context)))

    return blocks

@login_required
@jsonify
def reload_portal(request, block_id, ct_ids):
    context = RequestContext(request)
    blocks_manager = BlocksManager.get(context)
    ct_ids = str2list(ct_ids)
    depblock_ids = _get_depblock_ids(request, block_id)
    blocks = []

    for block_id in depblock_ids:
        block = block_registry[block_id]
        blocks_manager.add_group(block_id, block)
        blocks.append((block_id, block.portal_display(context, ct_ids)))

    return blocks

@login_required
@jsonify
def reload_basic(request, block_id):
    context = RequestContext(request)
    blocks_manager = BlocksManager.get(context)
    depblock_ids = _get_depblock_ids(request, block_id)
    blocks = []

    for block_id in depblock_ids:
        block = block_registry[block_id]
        blocks_manager.add_group(block_id, block)
        blocks.append((block_id, block.detailview_display(context)))

    return blocks
