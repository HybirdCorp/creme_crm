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

from functools import partial
import logging, warnings

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.template.context import make_context
from django.template.engine import Engine

from ..auth.decorators import login_required
from ..gui.bricks import brick_registry, str2list, BricksManager
from ..models import CremeEntity, BlockState
from ..utils import jsonify, get_ct_or_404


logger = logging.getLogger(__name__)


def build_context(request, **kwargs):
    warnings.warn('creme_core.views.blocks.build_context() is deprecated ; '
                  'use creme_core.views.bricks.build_context() instead.',
                  DeprecationWarning
                 )

    context = make_context({}, request)

    for processor in Engine.get_default().template_context_processors:
        context.update(processor(request))

    context.update(kwargs)  # Updated _after_ processors in order to avoid shadowing

    return context.flatten()


def _get_depblock_ids(request, block_id):
    warnings.warn('creme_core.views.blocks._get_depblock_ids() is deprecated ; '
                  'use creme_core.views.bricks.get_brick_ids() instead.',
                  DeprecationWarning
                 )

    ids = [block_id]

    posted_deps = request.GET.get(block_id + '_deps')
    if posted_deps:
        ids.extend(posted_deps.split(','))

    return ids


def _build_blocks_render(request, block_id, blocks_manager, block_render_function, check_permission=False):
    warnings.warn('creme_core.views.blocks._build_blocks_render() is deprecated ; '
                  'use creme_core.views.bricks._build_blocks_render() instead.',
                  DeprecationWarning
                 )

    block_renders = []
    blocks = brick_registry.get_blocks(_get_depblock_ids(request, block_id))

    if check_permission:
        has_perm = request.user.has_perm

        for block in blocks:
            try:
                permission = block.permission
            except AttributeError:
                logger.error('You should set "permission" on the block: %s (id=%s)', block.__class__, block.id_)
            else:
                if permission is not None and not has_perm(permission):
                    raise PermissionDenied('Error: you are not allowed to view this block: %s' % block.id_)

    for block in blocks:
        blocks_manager.add_group(block.id_, block)

    # Blocks are iterated twice for knowing all imported blocks when rendering
    # Used for caching states notably...
    for block in blocks:
        block_render = block_render_function(block)

        if block_render is not None:
            block_renders.append((block.id_, block_render))

    return block_renders


def _render_detail(block, context):
    warnings.warn('creme_core.views.blocks._render_detail() is deprecated ; '
                  'use creme_core.views.bricks._render_detail() instead.',
                  DeprecationWarning
                 )

    fun = getattr(block, 'detailview_display', None)

    if fun:
        return fun(context)

    logger.warn('Block without detailview_display() : %s (id=%s)', block.__class__, block.id_)


@login_required
@jsonify
def reload_detailview(request, block_id, entity_id):
    warnings.warn('creme_core.views.blocks.reload_detailview() is deprecated ; '
                  'use creme_core.views.bricks.reload_detailview() instead.',
                  DeprecationWarning
                 )

    entity = get_object_or_404(CremeEntity, pk=entity_id).get_real_entity()

    request.user.has_perm_to_view_or_die(entity)

    context = build_context(request, object=entity)

    return _build_blocks_render(request, block_id, BricksManager.get(context),
                                partial(_render_detail, context=context)
                                )


@login_required
@jsonify
def reload_home(request, block_id):
    warnings.warn('creme_core.views.blocks.reload_home() is deprecated ; '
                  'use creme_core.views.bricks.reload_home() instead.',
                  DeprecationWarning
                 )

    context = build_context(request)

    def render_home(block):
        fun = getattr(block, 'home_display', None)

        if fun:
            return fun(context)

        logger.warn('Block without home_display() : %s (id=%s)', block.__class__, block.id_)

    return _build_blocks_render(request, block_id, BricksManager.get(context), render_home)


@login_required
@jsonify
def reload_portal(request, block_id, ct_ids):
    warnings.warn('creme_core.views.blocks.reload_portal() is deprecated ; '
                  'use creme_core.views.bricks.reload_portal() instead.',
                  DeprecationWarning
                 )

    context = build_context(request)
    ct_ids = str2list(ct_ids)
    app_labels = {get_ct_or_404(ct_id).model_class()._meta.app_label for ct_id in ct_ids}

    if len(app_labels) != 1:
        raise PermissionDenied('Error: all ContentTypes must be related to the same app')

    app_label = iter(app_labels).next()

    if not request.user.has_perm(app_label):  # TODO: in a role method ??
        raise PermissionDenied('You are not allowed to access to the app: %s' % app_label)

    def render_portal(block):
        fun = getattr(block, 'portal_display', None)

        if fun:
            return fun(context, ct_ids)

        logger.warn('Block without portal_display() : %s (id=%s)', block.__class__, block.id_)

    return _build_blocks_render(request, block_id, BricksManager.get(context), render_portal)


@login_required
@jsonify
def reload_basic(request, block_id):
    """Blocks that uses this reloading view must have an attribute 'permission',
    which contains the string corresponding to the permission to view this block,
    eg: permission = "creme_config.can_admin"
    'permission = None' means 'no permission required' ; use with caution :)
    """
    warnings.warn('creme_core.views.blocks.reload_basic() is deprecated ; '
                  'use creme_core.views.bricks.reload_basic() instead.',
                  DeprecationWarning
                 )

    context = build_context(request)

    return _build_blocks_render(request, block_id, BricksManager.get(context),
                                partial(_render_detail, context=context),
                                check_permission=True
                               )


@login_required
@jsonify
def reload_relations_block(request, entity_id, relation_type_ids=''):
    warnings.warn('creme_core.views.blocks.reload_relations_block() is deprecated', DeprecationWarning)

    from ..blocks import relations_block

    entity = get_object_or_404(CremeEntity, pk=entity_id).get_real_entity()
    request.user.has_perm_to_view_or_die(entity)

    context = build_context(request, object=entity)
    blocks_manager = BricksManager.get(context)
    # blocks_manager.used_relationtypes_ids = (rtype_id for rtype_id in relation_type_ids.split(',') if rtype_id)
    blocks_manager.used_relationtypes_ids = excl_rtype_ids = [rtype_id for rtype_id in relation_type_ids.split(',') if rtype_id]

    # return _build_blocks_render(request, relations_block.id_, blocks_manager,
    #                             lambda block: block.detailview_display(context)
    #                            )
    def render_block(block):
        block._reloading_info = {'exclude': excl_rtype_ids}
        return block.detailview_display(context)

    return _build_blocks_render(request, relations_block.id_, blocks_manager, render_block)


@login_required
@jsonify
def set_state(request, block_id):
    warnings.warn('creme_core.views.blocks.set_state() is deprecated ; '
                  'use creme_core.views.bricks.set_state() instead.',
                  DeprecationWarning
                 )

    POST_get = request.POST.get
    is_open           = POST_get('is_open')
    show_empty_fields = POST_get('show_empty_fields')
    state_changed = False

    # TODO: Avoid the query if there is no post param?
    bs = BlockState.objects.get_or_create(block_id=block_id, user=request.user)[0]

    if is_open is not None:
        bs.is_open = bool(int(is_open))
        state_changed = True

    if show_empty_fields is not None:
        bs.show_empty_fields = bool(int(show_empty_fields))
        state_changed = True

    if state_changed:
        bs.save()
