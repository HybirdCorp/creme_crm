# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2017-2020  Hybird
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

from json import loads as json_load
import logging
import warnings
from typing import Dict, List, Tuple, Type

from django.core.exceptions import PermissionDenied
from django.http.response import HttpResponseBase, HttpResponse, Http404
from django.db import IntegrityError
# from django.shortcuts import get_object_or_404
from django.template.context import make_context
from django.template.engine import Engine

from .. import utils
# from ..auth.decorators import login_required
from ..gui.bricks import Brick, _BrickRegistry, brick_registry, BricksManager
from ..http import CremeJsonResponse
from ..models import BrickState  # CremeEntity

from . import generic
# from .decorators import jsonify

logger = logging.getLogger(__name__)


def build_context(request, **kwargs):
    warnings.warn('creme_core.views.bricks.build_context() is deprecated ; '
                  'use the class based view BricksReloading instead.',
                  DeprecationWarning
                 )

    context = make_context({}, request)

    for processor in Engine.get_default().template_context_processors:
        context.update(processor(request))

    context.update(kwargs)  # Updated _after_ processors in order to avoid shadowing

    return context.flatten()


def get_brick_ids_or_404(request):
    warnings.warn('creme_core.views.bricks.get_brick_ids_or_404() is deprecated ; '
                  'use the class based view BricksReloading instead.',
                  DeprecationWarning
                 )

    brick_ids = request.GET.getlist('brick_id')

    if not brick_ids:
        raise Http404('Empty "brick_id" list.')

    return brick_ids


def render_detailview_brick(brick, context):
    warnings.warn('creme_core.views.bricks.render_detailview_brick() is deprecated',
                  DeprecationWarning
                 )

    fun = getattr(brick, 'detailview_display', None)

    if fun:
        return fun(context)

    logger.warning('Brick without detailview_display(): %s (id=%s)', brick.__class__, brick.id_)


def render_home_brick(brick, context):
    warnings.warn('creme_core.views.bricks.render_home_brick() is deprecated',
                  DeprecationWarning
                 )

    fun = getattr(brick, 'home_display', None)

    if fun:
        return fun(context)

    logger.warning('Brick without home_display() : %s (id=%s)', brick.__class__, brick.id_)


def bricks_render_info(request, bricks, context=None,
                       brick_render_function=render_detailview_brick, check_permission=False):
    """Build a list of tuples (brick_ID, brick_HTML) which can be serialised to JSON.
    It is helpful for brick-reloading views.

    @param request: Classical 'request' argument of views.
    @param bricks: Iterable of Bricks instances.
    @param context: Dictionary used to render the template, or None (then a default one is used).
    @param brick_render_function: A callable which takes the 2 following arguments:
            - 'brick': a Brick instances (from 'bricks').
            - 'context': the template context (dictionary).
            See render_detailview_brick()/render_home_brick().
    @param check_permission: A boolean indicating if the attribute 'permission' of the bricks
           instances has to be checked.
    @return A JSON-friendly list of tuples.
    """
    warnings.warn('creme_core.views.bricks.bricks_render_info() is deprecated ; '
                  'use the class based view BricksReloading instead.',
                  DeprecationWarning
                 )

    from collections import Iterator

    # The sequence is iterated twice for knowing all imported bricks when rendering
    # (in order to cache the states notably...), so it cannot be a generator.
    if isinstance(bricks, Iterator):
        bricks = [*bricks]

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
                logger.error('You should set "permission" on the brick: %s (id=%s)',
                             brick.__class__, brick.id_,
                            )
            else:
                if permission is not None and not has_perm(permission):
                    raise PermissionDenied(
                        f'Error: you are not allowed to view this brick: {brick.id_}'
                    )

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
        brick_render = brick_render_function(brick, context={**context})

        if brick_render is not None:
            brick_renders.append((brick.id_, brick_render))

    return brick_renders


# @login_required
# @jsonify
# def reload_basic(request):
#     brick_ids = get_brick_ids_or_404(request)
#
#     return bricks_render_info(request,
#                               bricks=[*brick_registry.get_bricks(brick_ids)],
#                               check_permission=True,
#                              )
class BricksReloading(generic.CheckedView):
    """Bricks that uses this reloading view must have an attribute 'permission',
    which contains the string corresponding to the permission to view this brick,
    eg: permission = "creme_config.can_admin"
    'permission = None' means 'no permission required' ; use with caution :)
    """
    response_class: Type[HttpResponseBase] = CremeJsonResponse
    brick_registry: _BrickRegistry = brick_registry
    # Name of the Brick's render method to use ;
    # classically: "detailview_display" or "home_display".
    brick_render_method: str = 'detailview_display'
    # A boolean indicating if the attribute 'permission' of the bricks
    # instances has to be checked.
    check_bricks_permission: bool = True

    def get_brick_ids(self) -> List[str]:
        # TODO: filter empty IDs ??
        brick_ids = self.request.GET.getlist('brick_id')

        if not brick_ids:
            raise Http404('Empty "brick_id" list.')

        return brick_ids

    def get_bricks(self) -> List[Brick]:
        return [*self.brick_registry.get_bricks(self.get_brick_ids())]

    def get_bricks_contents(self) -> List[Tuple[str, str]]:
        """Build a list of tuples (brick_ID, brick_HTML) which can be serialised to JSON.

        @return A JSON-friendly list of tuples.
        """
        request = self.request
        brick_renders = []
        bricks = self.get_bricks()
        context = self.get_bricks_context().flatten()
        bricks_manager = BricksManager.get(context)

        if self.check_bricks_permission:
            has_perm = request.user.has_perm

            for brick in bricks:
                try:
                    permission = brick.permission
                except AttributeError:
                    logger.error(
                        'You should set "permission" on the brick: %s (id=%s)',
                        brick.__class__, brick.id_,
                    )
                else:
                    if permission is not None and not has_perm(permission):
                        raise PermissionDenied(
                            f'Error: you are not allowed to view this brick: {brick.id_}'
                        )

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

        render_method = self.brick_render_method
        for brick in bricks:
            reloading_info = all_reloading_info.get(brick.id_)
            if reloading_info is not None:
                brick.reloading_info = reloading_info

            render_func = getattr(brick, render_method, None)

            if render_func is None:
                logger.warning('Brick without %s(): %s (id=%s)',
                               render_method, brick.__class__, brick.id_,
                              )
            else:
                # NB: the context is copied is order to a 'fresh' one for each brick, & so avoid annoying side-effects
                # Notice that build_context() creates a shared dictionary with the "shared" key in order to explicitly
                # share data between 2+ bricks.
                brick_renders.append((brick.id_, render_func({**context})))

        return brick_renders

    def get_bricks_context(self):
        request = self.request
        context = make_context({}, request)

        for processor in Engine.get_default().template_context_processors:
            context.update(processor(request))

        return context

    def get(self, request, **kwargs):
        return self.response_class(
            self.get_bricks_contents(),
            safe=False,  # Result is not a dictionary
        )


# @login_required
# @jsonify
# def reload_detailview(request, entity_id):
#     brick_ids = get_brick_ids_or_404(request)
#
#     entity = get_object_or_404(CremeEntity, pk=entity_id).get_real_entity()
#     request.user.has_perm_to_view_or_die(entity)
#
#     return bricks_render_info(request,
#                               bricks=[*brick_registry.get_bricks(brick_ids, entity=entity)],
#                               context=build_context(request, object=entity),
#                              )
class DetailviewBricksReloading(generic.base.EntityRelatedMixin, BricksReloading):
    check_bricks_permission = False

    def check_related_entity_permissions(self, entity, user):
        user.has_perm_to_view_or_die(entity)

    def get_bricks(self):
        return [
            *self.brick_registry.get_bricks(self.get_brick_ids(),
                                            entity=self.get_related_entity(),
                                           )
        ]

    def get_bricks_context(self):
        context = super().get_bricks_context()
        context['object'] = self.get_related_entity()

        return context


# @login_required
# @jsonify
# def reload_home(request):
#     return bricks_render_info(request,
#                               bricks=[*brick_registry.get_bricks(get_brick_ids_or_404(request))],
#                               brick_render_function=render_home_brick,
#                              )
class HomeBricksReloading(BricksReloading):
    check_bricks_permission = False
    brick_render_method = 'home_display'


class BrickStateSetting(generic.CheckedView):
    brick_id_arg: str = 'id'
    FIELDS: List[Tuple[str, str]] = [
        # MODEL FIELD         POST ARGUMENT
        ('is_open',           'is_open'),
        ('show_empty_fields', 'show_empty_fields'),
    ]

    def get_fields_to_update(self, request) -> Dict[str, bool]:
        fields_2_update = {}
        get = request.POST.get

        for field_name, post_key in self.FIELDS:
            value_str = get(post_key)

            if value_str is not None:
                fields_2_update[field_name] = utils.bool_from_str_extended(value_str)

        return fields_2_update

    def post(self, request, **kwargs):
        # TODO: check that brick ID is valid ?
        brick_id = utils.get_from_POST_or_404(request.POST, self.brick_id_arg)
        fields_2_update = self.get_fields_to_update(request)

        if fields_2_update:
            # NB: we can still have a race condition because we do not use select_for_update ;
            #     but it's a state related one user & one brick, so it would not be a real world problem.
            for _i in range(10):
                state = BrickState.objects.get_for_brick_id(brick_id=brick_id, user=request.user)

                try:
                    utils.update_model_instance(state, **fields_2_update)
                except IntegrityError:
                    logger.exception('Avoid a duplicate.')
                    continue
                else:
                    break

        return HttpResponse()
