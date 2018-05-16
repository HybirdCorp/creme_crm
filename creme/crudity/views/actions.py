# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

# import warnings

from django.core.exceptions import PermissionDenied
from django.db.transaction import atomic
from django.http import HttpResponse, Http404
from django.shortcuts import render, get_list_or_404
from django.urls import reverse
from django.utils.translation import ugettext as _

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.utils import jsonify
from creme.creme_core.views.bricks import bricks_render_info, get_brick_ids_or_404
from creme.creme_core.views.decorators import POST_only

from .. import registry
# from ..bricks import WaitingActionsBrick
from ..models import WaitingAction


def _retrieve_actions_ids(request):
    return request.POST.getlist('ids')


# def _fetch(user):
#     warnings.warn('crudity.views.actions._fetch() is deprecated ; '
#                   'use crudity_registry.fetch() instead.',
#                   DeprecationWarning
#                  )
#
#     return len(registry.crudity_registry.fetch(user))


def _build_portal_bricks():
    # bricks = []
    #
    # for backend in registry.crudity_registry.get_configured_backends():
    #     if backend.in_sandbox:
    #         brick_classes = backend.blocks or (WaitingActionsBrick,)
    #
    #         for brick_class in brick_classes:
    #             bricks.append(brick_class(backend))
    #
    # return bricks
    return [
        brick_class(backend)
            for backend in registry.crudity_registry.get_configured_backends()
                if backend.in_sandbox
                    for brick_class in backend.brick_classes
    ]


@login_required
@permission_required('crudity')
def portal(request):
    return render(request, template_name='crudity/waiting-actions.html',
                  context={'bricks': _build_portal_bricks(),
                           'bricks_reload_url': reverse('crudity__reload_actions_bricks'),
                          },
                 )


@login_required
@permission_required('crudity')
@POST_only
@jsonify
def refresh(request):
    return [backend.get_id() for backend in registry.crudity_registry.fetch(request.user)]


@login_required
@permission_required('crudity')
@POST_only
def delete(request):
    actions_ids = _retrieve_actions_ids(request)
    user = request.user
    errors = []

    if actions_ids:
        for action in WaitingAction.objects.filter(id__in=actions_ids):
            allowed, message = action.can_validate_or_delete(user)
            if allowed:
                action.delete()
            else:
                errors.append(message)

    if not errors:
        status = 200
        message = _(u'Operation successfully completed')
    else:
        status = 400
        message = ','.join(errors)

    # return HttpResponse(message, content_type='text/javascript', status=status)
    return HttpResponse(message, status=status)


@jsonify
@permission_required('crudity')
@POST_only
def validate(request):
    actions = get_list_or_404(WaitingAction, pk__in=_retrieve_actions_ids(request))

    for action in actions:
        allowed, message = action.can_validate_or_delete(request.user)

        if not allowed:
            raise PermissionDenied(message)

        source_parts = action.source.split(' - ', 1)

        try:
            if len(source_parts) == 1:
                backend = registry.crudity_registry.get_default_backend(source_parts[0])
            elif len(source_parts) == 2:
                backend = registry.crudity_registry.get_configured_backend(*source_parts, norm_subject=action.subject)
            else:
                raise ValueError('Malformed source')
        except (KeyError, ValueError) as e:
            raise Http404('Invalid backend for WaitingAction(id=%s, source=%s): %s' % (
                                action.id, action.source, e,
                            )
                         )

        with atomic():
            is_created = backend.create(action)

            if is_created:
                action.delete()
            # else: Add a message for the user

    return {}


# @jsonify
# @permission_required('crudity')
# def reload_block(request, block_id):
#     warnings.warn('crudity.views.actions.reload_block() is deprecated ; '
#                   'use crudity.views.actions.reload_bricks() instead.',
#                   DeprecationWarning
#                  )
#
#     from creme.creme_core.views.blocks import build_context as blocks_build_context
#
#     prefix = 'block_crudity-waiting_actions-'
#
#     if not block_id.startswith(prefix):
#         raise Http404('Invalid block ID (bad prefix)')
#
#     block_id = block_id[len(prefix):]
#     parts = block_id.split('|', 2)
#     length = len(parts)
#
#     if length == 3:
#         try:
#             # NB: arguments are fetcher_name, input_name, norm_subject
#             backend = registry.crudity_registry.get_configured_backend(*parts)
#         except KeyError as e:
#             raise Http404(e)
#     elif length == 1:
#         try:
#             backend = registry.crudity_registry.get_default_backend(parts[0])
#         except KeyError as e:
#             raise Http404(e)
#     else:
#         raise Http404('Invalid block ID (bad backend info)')
#
#     block = WaitingActionsBrick(backend)
#
#     return [(block.id_, block.detailview_display(blocks_build_context(request)))]


@permission_required('crudity')
@jsonify
def reload_bricks(request):
    brick_ids = get_brick_ids_or_404(request)
    bricks = []
    get_brick = {brick.id_: brick for brick in _build_portal_bricks()}.get

    for brick_id in brick_ids:
        brick = get_brick(brick_id)

        if not brick:
            raise Http404('Invalid brick ID: ' + brick_id)

        bricks.append(brick)

    return bricks_render_info(request, bricks=bricks)


# @login_required
# @permission_required('crudity')
# def fetch(request, template='crudity/waiting_actions.html',
#           ajax_template='crudity/frags/ajax/waiting_actions.html',
#           extra_tpl_ctx=None, extra_req_ctx=None):
#     warnings.warn('crudity.views.actions.fetch() is deprecated.', DeprecationWarning)
#
#     from django.shortcuts import render_to_response
#     from django.template.loader import render_to_string
#
#     from creme.creme_core.views.blocks import build_context as blocks_build_context
#
#     context = blocks_build_context(request)
#
#     if extra_req_ctx:
#         context.update(extra_req_ctx)
#
#     _fetch(request.user)
#
#     context['blocks'] = [''.join(block(backend).detailview_display(context) for block in backend.blocks)
#                          or WaitingActionsBrick(backend).detailview_display(context)
#                             for backend in registry.crudity_registry.get_configured_backends()
#                                 if backend.in_sandbox
#                         ]
#
#     if extra_tpl_ctx:
#         context.update(extra_tpl_ctx)
#
#     if request.is_ajax():
#         return HttpResponse(render_to_string(ajax_template, context))
#
#     return render_to_response(template, context)
