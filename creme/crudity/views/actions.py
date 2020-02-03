# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

from typing import Iterator, List

from django.core.exceptions import PermissionDenied
from django.db.transaction import atomic
from django.http import HttpResponse, Http404
# from django.shortcuts import get_list_or_404
from django.utils.translation import gettext as _

# from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.core.exceptions import BadRequestError
from creme.creme_core.gui.bricks import Brick
from creme.creme_core.http import CremeJsonResponse
from creme.creme_core.shortcuts import get_bulk_or_404
from creme.creme_core.views import generic
from creme.creme_core.views.bricks import BricksReloading  # bricks_render_info, get_brick_ids_or_404
# from creme.creme_core.views.decorators import jsonify, POST_only

from .. import registry
from ..models import WaitingAction
from ..backends.models import CrudityBackend


# def _retrieve_actions_ids(request):
#     return request.POST.getlist('ids')


class RegistryMixin:
    crudity_registry = registry.crudity_registry


class ActionsMixin:
    action_ids_arg = 'ids'

    def get_action_ids(self, request) -> List[int]:
        try:
            ids = [int(i) for i in request.POST.getlist(self.action_ids_arg)]
        except ValueError as e:
            raise BadRequestError(str(e)) from e

        if not ids:
            raise BadRequestError('Empty list of IDs')

        return ids

    def get_actions(self, request) -> Iterator[WaitingAction]:
        return iter(get_bulk_or_404(WaitingAction, self.get_action_ids(request)).values())


# def _build_portal_bricks():
#     return [
#         brick_class(backend)
#             for backend in registry.crudity_registry.get_configured_backends()
#                 if backend.in_sandbox
#                     for brick_class in backend.brick_classes
#     ]
class PortalBricksMixin(RegistryMixin):
    def get_portal_bricks(self) -> List[Brick]:
        return [
            brick_class(backend)
                for backend in self.crudity_registry.get_configured_backends()
                    if backend.in_sandbox
                        for brick_class in backend.brick_classes
        ]


class Portal(PortalBricksMixin, generic.BricksView):
    template_name = 'crudity/waiting-actions.html'
    permissions = 'crudity'
    bricks_reload_url_name = 'crudity__reload_actions_bricks'

    def get_bricks(self):
        # return _build_portal_bricks()
        return self.get_portal_bricks()


# @login_required
# @permission_required('crudity')
# @POST_only
# @jsonify
# def refresh(request):
#     return [backend.get_id() for backend in registry.crudity_registry.fetch(request.user)]
class ActionsRefreshing(RegistryMixin, generic.CheckedView):
    permissions = 'crudity'
    response_class = CremeJsonResponse

    def refresh(self, user) -> List[CrudityBackend]:
        return self.crudity_registry.fetch(user)

    def post(self, request, *args, **kwargs):
        return self.response_class(
            [backend.get_id() for backend in self.refresh(request.user)],
            safe=False,  # Result is not a dictionary
        )


# @login_required
# @permission_required('crudity')
# @POST_only
# def delete(request):
#     actions_ids = _retrieve_actions_ids(request)
#     user = request.user
#     errors = []
#
#     if actions_ids:
#         for action in WaitingAction.objects.filter(id__in=actions_ids):
#             allowed, message = action.can_validate_or_delete(user)
#             if allowed:
#                 action.delete()
#             else:
#                 errors.append(message)
#
#     if not errors:
#         status = 200
#         message = _('Operation successfully completed')
#     else:
#         status = 400
#         message = ','.join(errors)
#
#     return HttpResponse(message, status=status)
class ActionsDeletion(ActionsMixin, generic.CheckedView):
    permissions = 'crudity'

    def post(self, request, *args, **kwargs):
        user = request.user
        errors = []

        for action in self.get_actions(request):
            allowed, message = action.can_validate_or_delete(user)
            if allowed:
                action.delete()
            else:
                errors.append(message)

        if not errors:
            status = 200
            message = _('Operation successfully completed')
        else:
            status = 400
            message = ','.join(errors)

        return HttpResponse(message, status=status)


# @jsonify
# @login_required
# @permission_required('crudity')
# @POST_only
# def validate(request):
#     actions = get_list_or_404(WaitingAction, pk__in=_retrieve_actions_ids(request))
#
#     for action in actions:
#         allowed, message = action.can_validate_or_delete(request.user)
#
#         if not allowed:
#             raise PermissionDenied(message)
#
#         source_parts = action.source.split(' - ', 1)
#
#         try:
#             if len(source_parts) == 1:
#                 backend = registry.crudity_registry.get_default_backend(source_parts[0])
#             elif len(source_parts) == 2:
#                 backend = registry.crudity_registry.get_configured_backend(*source_parts, norm_subject=action.subject)
#             else:
#                 raise ValueError('Malformed source')
#         except (KeyError, ValueError) as e:
#             raise Http404('Invalid backend for WaitingAction(id={}, source={}): {}'.format(
#                                 action.id, action.source, e,
#                             )
#                          ) from e
#
#         with atomic():
#             is_created = backend.create(action)
#
#             if is_created:
#                 action.delete()
#             # else: Add a message for the user
#
#     return {}
class ActionsValidation(RegistryMixin, ActionsMixin, generic.CheckedView):
    permissions = 'crudity'

    def get_backend(self, action: WaitingAction) -> CrudityBackend:
        source_parts: List[str] = action.source.split(' - ', 1)

        try:
            if len(source_parts) == 1:
                backend = self.crudity_registry.get_default_backend(source_parts[0])
            elif len(source_parts) == 2:
                backend = self.crudity_registry.get_configured_backend(
                    fetcher_name=source_parts[0],
                    input_name=source_parts[1],
                    norm_subject=action.subject,
                )
            else:
                raise ValueError('Malformed source')
        except (KeyError, ValueError) as e:
            raise Http404(
                f'Invalid backend for WaitingAction(id={action.id}, source={action.source}): {e}'
            ) from e

        return backend

    def post(self, request, *args, **kwargs):
        for action in self.get_actions(request):
            allowed, message = action.can_validate_or_delete(request.user)

            if not allowed:
                raise PermissionDenied(message)

            backend = self.get_backend(action)

            with atomic():
                is_created = backend.create(action)

                if is_created:
                    action.delete()
                # else: Add a message for the user

        return HttpResponse()


# @login_required
# @permission_required('crudity')
# @jsonify
# def reload_bricks(request):
#     brick_ids = get_brick_ids_or_404(request)
#     bricks = []
#     get_brick = {brick.id_: brick for brick in _build_portal_bricks()}.get
#
#     for brick_id in brick_ids:
#         brick = get_brick(brick_id)
#
#         if not brick:
#             raise Http404('Invalid brick ID: ' + brick_id)
#
#         bricks.append(brick)
#
#     return bricks_render_info(request, bricks=bricks)
class ActionsBricksReloading(PortalBricksMixin, BricksReloading):
    check_bricks_permission = False
    permissions = 'crudity'

    def get_bricks(self):
        bricks = []
        get_brick = {brick.id_: brick for brick in self.get_portal_bricks()}.get

        for brick_id in self.get_brick_ids():
            brick = get_brick(brick_id)

            if not brick:
                raise Http404('Invalid brick ID: ' + brick_id)

            bricks.append(brick)

        return bricks
