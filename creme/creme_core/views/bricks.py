################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2017-2025  Hybird
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
from json import loads as json_load

from django.db import IntegrityError
from django.http.response import Http404, HttpResponse, HttpResponseBase
from django.template.context import make_context
from django.template.engine import Engine

from .. import utils
from ..gui.bricks import Brick, BrickManager, BrickRegistry, VoidBrick
from ..gui.bricks import brick_registry as global_brick_registry
from ..http import CremeJsonResponse
from ..models import BrickState
from . import generic

logger = logging.getLogger(__name__)


class BricksReloading(generic.CheckedView):
    """This reloading view uses the attribute 'permissions' of the bricks,
    which contains the string(s) corresponding to the permissions to view a brick,
    e.g. <permissions = "creme_config.can_admin">

    Recall: the default value <permissions = ''> means 'no permission required' ;
            use with caution :)
    """
    response_class: type[HttpResponseBase] = CremeJsonResponse
    brick_registry: BrickRegistry = global_brick_registry
    # Name of the Brick's render method to use ;
    # classically: "detailview_display" or "home_display".
    brick_render_method: str = 'detailview_display'

    def get_brick_ids(self) -> list[str]:
        # TODO: filter empty IDs ??
        brick_ids = self.request.GET.getlist('brick_id')

        if not brick_ids:
            raise Http404('Empty "brick_id" list.')

        return brick_ids

    def get_bricks(self) -> list[Brick]:
        return [
            *self.brick_registry.get_bricks(
                brick_ids=self.get_brick_ids(),
                user=self.request.user,
            ),
        ]

    def get_bricks_contents(self) -> list[tuple[str, str]]:
        """Build a list of tuples (brick_ID, brick_HTML) which can be serialised to JSON.

        @return A JSON-friendly list of tuples.
        """
        request = self.request
        brick_renders = []
        bricks = self.get_bricks()
        context = self.get_bricks_context().flatten()
        bricks_manager = BrickManager.get(context)

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
            bricks_manager.add_group(f'group-{id(brick)}', brick)

        render_method = self.brick_render_method
        for brick in bricks:
            reloading_info = all_reloading_info.get(brick.id)
            if reloading_info is not None:
                brick.reloading_info = reloading_info

            render_func = getattr(brick, render_method, None)

            if render_func is None:
                logger.warning(
                    'Brick without %s(): %s (id=%s)',
                    render_method, brick.__class__, brick.id,
                )
            else:
                # NB: the context is copied is order to a 'fresh' one for each
                # brick, & so avoid annoying side effects.
                # Notice that build_context() creates a shared dictionary with
                # the "shared" key in order to explicitly share data between 2+ bricks.
                brick_renders.append((brick.id, render_func({**context})))

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


class DetailviewBricksReloading(generic.base.EntityRelatedMixin, BricksReloading):
    def check_related_entity_permissions(self, entity, user):
        user.has_perm_to_view_or_die(entity)

    def get_bricks(self):
        bricks = []
        entity = self.get_related_entity()
        model = type(entity)

        for brick in self.brick_registry.get_bricks(
            brick_ids=self.get_brick_ids(),
            entity=entity,
            user=self.request.user,
        ):
            target_ctypes = brick.target_ctypes
            if target_ctypes and model not in target_ctypes:
                brick = VoidBrick(id=brick.id)

            bricks.append(brick)

        return bricks

    def get_bricks_context(self):
        context = super().get_bricks_context()
        context['object'] = self.get_related_entity()

        return context


class HomeBricksReloading(BricksReloading):
    brick_render_method = 'home_display'


class BrickStateSetting(generic.CheckedView):
    brick_id_arg: str = 'brick_id'
    FIELDS: list[tuple[str, str]] = [
        # MODEL FIELD         POST ARGUMENT
        ('is_open',           'is_open'),
        ('show_empty_fields', 'show_empty_fields'),
    ]

    def get_fields_to_update(self, request) -> dict[str, bool]:
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
            # NB: we can still have a race condition because we do not use
            #     select_for_update() ; but it's a state related one user & one
            #     brick, so it would not be a real world problem.
            for _i in range(10):
                state = BrickState.objects.get_for_brick_id(
                    brick_id=brick_id, user=request.user,
                )

                try:
                    utils.update_model_instance(state, **fields_2_update)
                except IntegrityError:
                    logger.exception('Avoid a duplicate.')
                    continue
                else:
                    break

        return HttpResponse()


class BrickStateExtraDataSetting(generic.CheckedView):
    """Base view to set the extra data of a BrickState instance.
     The default behaviour is to set boolean values, but you can customise your
     view by overriding the method 'cast_value()' in your own view.

     In your custom view you should at least set the classes attributes
     "brick_cls" & "data_key".
     """
    value_arg: str = 'value'
    brick_cls: type[Brick] = Brick
    data_key: str = ''

    @staticmethod
    def cast_value(value):
        return utils.bool_from_str_extended(value)

    def get_value(self):
        return utils.get_from_POST_or_404(
            self.request.POST, key=self.value_arg, cast=self.cast_value,
        )

    def set_value(self, state: BrickState, value) -> None:
        if value is None:  # TODO: self.delete_on_none ?
            try:
                state.del_extra_data(self.data_key)
            except KeyError:
                pass
            else:
                state.save()
        elif state.set_extra_data(key=self.data_key, value=value):
            state.save()

    def post(self, request, **kwargs):
        value = self.get_value()

        # NB: we can still have a race condition because we do not use
        #     select_for_update ; but it's a state related to one user & one brick,
        #     so it would not be a real world problem.
        for _i in range(10):
            state = BrickState.objects.get_for_brick_id(
                brick_id=self.brick_cls.id, user=request.user,
            )

            try:
                self.set_value(state, value)
            except IntegrityError:
                logger.exception('Avoid a duplicate.')
                continue
            else:
                break

        return HttpResponse()
