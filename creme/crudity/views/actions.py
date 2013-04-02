# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response, get_list_or_404
from django.template.context import RequestContext
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required, permission_required

from creme.creme_core.utils import get_ct_or_404, jsonify

from ..models import WaitingAction
from ..registry import crudity_registry
from ..blocks import WaitingActionBlock


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
        message = _(u"Operation successfully completed")
    else:
        status = 400
        message = ",".join(errors)

    return HttpResponse(message, mimetype="text/javascript", status=status)

@jsonify
@permission_required('crudity')
def validate(request):
    actions = get_list_or_404(WaitingAction, pk__in=_retrieve_actions_ids(request))

    for action in actions:
        allowed, message = action.can_validate_or_delete(request.user)

        if not allowed:
            raise PermissionDenied(message)

        backend = crudity_registry.get_configured_backend(action.subject)

        is_created = backend.create(action)

        if is_created:
            action.delete()
        #else: Add a message for the user

    return {}
#    return HttpResponse()

@jsonify
@permission_required('crudity')
def reload(request, ct_id, backend_subject):
    get_ct_or_404(ct_id) #TODO: useless ??
    backend = crudity_registry.get_configured_backend(backend_subject)
    if not backend:
        raise Http404()

    block = WaitingActionBlock(backend)
    ctx = RequestContext(request)

    return [(block.id_, block.detailview_display(ctx))]

def _fetch(user):
    count = 0
    for fetcher in crudity_registry.get_fetchers():
        all_data = fetcher.fetch()
        inputs    = fetcher.get_inputs()
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
def fetch(request, template="crudity/waiting_actions.html", ajax_template="crudity/frags/ajax/waiting_actions.html", extra_tpl_ctx=None, extra_req_ctx=None):
    context = RequestContext(request)

    if extra_req_ctx:
        context.update(extra_req_ctx)

    _fetch(request.user)

    tpl_dict = {'blocks': ["".join(block(backend).detailview_display(context) for block in backend.blocks) or WaitingActionBlock(backend).detailview_display(context) for backend in crudity_registry.get_configured_backends() if backend.in_sandbox]}

    if extra_tpl_ctx:
        tpl_dict.update(extra_tpl_ctx)

    if request.is_ajax():
        return HttpResponse(render_to_string(ajax_template, tpl_dict, context_instance=context))

    return render_to_response(template, tpl_dict, context_instance=context)
