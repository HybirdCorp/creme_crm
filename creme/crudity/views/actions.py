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

from django.core.exceptions import PermissionDenied
from django.db.transaction import atomic
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response, get_list_or_404
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.utils import get_ct_or_404, jsonify
from creme.creme_core.views import blocks as blocks_views

from .. import registry
from ..blocks import WaitingActionBlock
from ..models import WaitingAction
# from ..registry import crudity_registry


def _retrieve_actions_ids(request):
    return request.POST.getlist('ids')


@login_required
@permission_required('crudity')
def delete(request):
    actions_ids = _retrieve_actions_ids(request)
    user = request.user
    errors = []

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

    return HttpResponse(message, content_type='text/javascript', status=status)


@jsonify
@permission_required('crudity')
def validate(request):
    actions = get_list_or_404(WaitingAction, pk__in=_retrieve_actions_ids(request))

    for action in actions:
        allowed, message = action.can_validate_or_delete(request.user)

        if not allowed:
            raise PermissionDenied(message)

        # backend = crudity_registry.get_configured_backend(action.subject)
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
# def reload(request, ct_id, backend_subject):
#     get_ct_or_404(ct_id)  # TODO: useless ??
#     backend = crudity_registry.get_configured_backend(backend_subject)
#     if not backend:
#         raise Http404()
#
#     block = WaitingActionBlock(backend)
#     ctx = blocks_views.build_context(request)
#
#     return [(block.id_, block.detailview_display(ctx))]
@jsonify
@permission_required('crudity')
def reload_block(request, block_id):
    prefix = 'block_crudity-waiting_actions-'

    if not block_id.startswith(prefix):
        raise Http404('Invalid block ID (bad prefix)')

    block_id = block_id[len(prefix):]
    parts = block_id.split('|', 2)
    length = len(parts)

    if length == 3:
        try:
            # NB: arguments are fetcher_name, input_name, norm_subject
            backend = registry.crudity_registry.get_configured_backend(*parts)
        except KeyError as e:
            raise Http404(e)
    elif length == 1:
        try:
            backend = registry.crudity_registry.get_default_backend(parts[0])
        except KeyError as e:
            raise Http404(e)
    else:
        raise Http404('Invalid block ID (bad backend info)')

    block = WaitingActionBlock(backend)

    return [(block.id_, block.detailview_display(blocks_views.build_context(request)))]


def _fetch(user):
    count = 0

    for fetcher in registry.crudity_registry.get_fetchers():
        all_data = fetcher.fetch()
        inputs = fetcher.get_inputs()

        for data in all_data:
            handled = False

            for crud_inputs in inputs:
                for input_type, input in crud_inputs.iteritems():
                    handled = input.handle(data)

                    if handled:
                        break

                if handled:
                    count += 1
                    break

            if not handled:
                default_backend = fetcher.get_default_backend()

                if default_backend is not None:
                    count += 1
                    default_backend.fetcher_fallback(data, user)

    return count


@login_required
@permission_required('crudity')
def fetch(request, template='crudity/waiting_actions.html',
          ajax_template='crudity/frags/ajax/waiting_actions.html',
          extra_tpl_ctx=None, extra_req_ctx=None):
    context = blocks_views.build_context(request)

    if extra_req_ctx:
        context.update(extra_req_ctx)

    _fetch(request.user)

    context['blocks'] = [''.join(block(backend).detailview_display(context) for block in backend.blocks)
                         or WaitingActionBlock(backend).detailview_display(context)
                            for backend in registry.crudity_registry.get_configured_backends()
                                if backend.in_sandbox
                      ]

    if extra_tpl_ctx:
        # TODO: remove one argument between extra_req_ctx & extra_tpl_ctx
        context.update(extra_tpl_ctx)

    if request.is_ajax():
        return HttpResponse(render_to_string(ajax_template, context))

    return render_to_response(template, context)
