# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2017-2018  Hybird
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

from collections import Iterator
# from functools import partial
from json import loads as json_load
import logging
# import warnings

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.template.context import make_context
from django.template.engine import Engine

from ..auth.decorators import login_required
from ..gui.bricks import brick_registry, BricksManager
from ..models import CremeEntity, BrickState
from ..utils import jsonify, get_from_POST_or_404  # get_ct_or_404


logger = logging.getLogger(__name__)


def build_context(request, **kwargs):
    context = make_context({}, request)

    for processor in Engine.get_default().template_context_processors:
        context.update(processor(request))

    context.update(kwargs)  # Updated _after_ processors in order to avoid shadowing

    return context.flatten()


def get_brick_ids_or_404(request):
    # TODO: filter empty IDs ??
    brick_ids = request.GET.getlist('brick_id')

    if not brick_ids:
        raise Http404('Empty "brick_id" list.')

    return brick_ids


def render_detailview_brick(brick, context):
    fun = getattr(brick, 'detailview_display', None)

    if fun:
        return fun(context)

    logger.warning('Brick without detailview_display(): %s (id=%s)', brick.__class__, brick.id_)


def render_home_brick(brick, context):
    fun = getattr(brick, 'home_display', None)

    if fun:
        return fun(context)

    logger.warning('Brick without home_display() : %s (id=%s)', brick.__class__, brick.id_)


# def render_portal_brick(brick, context, ct_ids):
#     warnings.warn('creme_core.views.bricks.render_portal_brick() is deprecated.', DeprecationWarning)
#
#     fun = getattr(brick, 'portal_display', None)
#
#     if fun:
#         return fun(context, ct_ids)
#
#     logger.warn('Brick without portal_display() : %s (id=%s)', brick.__class__, brick.id_)


def bricks_render_info(request, bricks, context=None,
                       brick_render_function=render_detailview_brick, check_permission=False):
    """Build a list of tuples (brick_ID, brick_HTML) which can be serialised to JSON.
    It is helpful for brick-reloading views.

    @param request: Classical 'request' argument of views.
    @param bricks: Iterable of Bricks instances.
    @param context: Dictionnary used to render the template, or None (then a default one is used).
    @param brick_render_function: A callable which takes the 2 following arguments:
            - 'brick': a Brick instances (from 'bricks').
            - 'context': the template context (dictionnary).
            See render_detailview_brick()/render_home_brick().
    @param check_permission: A boolean indicating if the attribute 'permission' of the bricks
           instances has to be checked.
    @return A JSON-friendly list of tuples.
    """
    # The sequence is iterated twice for knowing all imported bricks when rendering
    # (in order to cache the states notably...), so it cannot be a generator.
    if isinstance(bricks, Iterator):
        bricks = list(bricks)

    brick_renders = []

    if context is None:
        context = build_context(request)

    bricks_manager = BricksManager.get(context)

    if check_permission:
        has_perm = request.user.has_perm

        for brick in bricks:
            try:
                permission = brick.permission
            except AttributeError:
                logger.error('You should set "permission" on the brick: %s (id=%s)', brick.__class__, brick.id_)
            else:
                if permission is not None and not has_perm(permission):
                    raise PermissionDenied('Error: you are not allowed to view this brick: {}'.format(brick.id_))

    all_reloading_info = {}
    all_reloading_info_json = request.GET.get('extra_data')
    if all_reloading_info_json is not None:
        try:
            decoded_reloading_info = json_load(all_reloading_info_json)
        except ValueError as e:
            logger.warning('Invalid "extra_data" parameter: %s.', e)
        else:
            if not isinstance(decoded_reloading_info, dict):
                logger.warning('Invalid "extra_data" parameter (not a dict).')
            else:
                all_reloading_info = decoded_reloading_info

    # TODO: only one group (add_group should not take *bricks, because the length is limited)
    for brick in bricks:
        bricks_manager.add_group(brick.id_, brick)

    for brick in bricks:
        reloading_info = all_reloading_info.get(brick.id_)
        if reloading_info is not None:
            brick.reloading_info = reloading_info

        # brick_render = brick_render_function(brick, context=context)
        # NB: the context is copied is order to a 'fresh' one for each brick, & so avoid annoying side-effects
        # Notice that build_context() creates a shared dictionary with the "shared" key in order to explicitly
        # share data between 2+ bricks.
        brick_render = brick_render_function(brick, context=dict(context))

        if brick_render is not None:
            brick_renders.append((brick.id_, brick_render))

    return brick_renders


@login_required
@jsonify
def reload_basic(request):
    """Bricks that uses this reloading view must have an attribute 'permission',
    which contains the string corresponding to the permission to view this brick,
    eg: permission = "creme_config.can_admin"
    'permission = None' means 'no permission required' ; use with caution :)
    """
    brick_ids = get_brick_ids_or_404(request)

    return bricks_render_info(request,
                              bricks=list(brick_registry.get_bricks(brick_ids)),
                              check_permission=True,
                             )


@login_required
@jsonify
def reload_detailview(request, entity_id):
    brick_ids = get_brick_ids_or_404(request)

    entity = get_object_or_404(CremeEntity, pk=entity_id).get_real_entity()
    request.user.has_perm_to_view_or_die(entity)

    return bricks_render_info(request,
                              bricks=list(brick_registry.get_bricks(brick_ids, entity=entity)),
                              context=build_context(request, object=entity),
                             )


@login_required
@jsonify
def reload_home(request):
    return bricks_render_info(request,
                              bricks=list(brick_registry.get_bricks(get_brick_ids_or_404(request))),
                              brick_render_function=render_home_brick,
                             )


# @login_required
# @jsonify
# def reload_portal(request):
#     warnings.warn('creme_core.views.bricks.reload_portal() is deprecated.', DeprecationWarning)
#
#     brick_ids = get_brick_ids_or_404(request)
#     ct_ids = request.GET.getlist('ct_id')
#     app_labels = {get_ct_or_404(ct_id).model_class()._meta.app_label for ct_id in ct_ids}
#
#     if len(app_labels) != 1:
#         raise PermissionDenied('Error: all ContentTypes must be related to the same app')
#
#     app_label = iter(app_labels).next()
#
#     if not request.user.has_perm(app_label):  # todo: in a role method ??
#         raise PermissionDenied('You are not allowed to access to the app: %s' % app_label)
#
#     return bricks_render_info(request,
#                               bricks=list(brick_registry.get_bricks(brick_ids)),
#                               brick_render_function=partial(render_portal_brick, ct_ids=ct_ids),
#                              )


@login_required
@jsonify
def set_state(request):
    POST = request.POST

    # TODO: check that brick ID is valid ?
    brick_id = get_from_POST_or_404(POST, 'id')

    POST_get = POST.get
    is_open           = POST_get('is_open')
    show_empty_fields = POST_get('show_empty_fields')
    state_changed = False

    # TODO: Avoid the query if there is no post param?
    bs = BrickState.objects.get_or_create(brick_id=brick_id, user=request.user)[0]

    if is_open is not None:
        bs.is_open = bool(int(is_open))
        state_changed = True

    if show_empty_fields is not None:
        bs.show_empty_fields = bool(int(show_empty_fields))
        state_changed = True

    if state_changed:
        bs.save()
