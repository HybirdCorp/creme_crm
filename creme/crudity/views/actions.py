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

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.template.context import RequestContext

from creme_core.utils import get_ct_or_404, jsonify

from crudity import VERBOSE_CRUD
from crudity.models.actions import WaitingAction
from crudity.backends.registry import from_email_crud_registry
from crudity.blocks import WaitingActionBlock

def _retrieve_actions_ids(request):
    return request.POST.getlist('ids')

@login_required
@permission_required('crudity')
def delete(request):
    #TODO: There no verifications because email is not a CremeEntity!!!
    for id in _retrieve_actions_ids(request):
        action = get_object_or_404(WaitingAction, pk=id)
        action.delete()

    return HttpResponse()

@jsonify
@permission_required('crudity')
def validate(request):
    for id in _retrieve_actions_ids(request):
        action = get_object_or_404(WaitingAction, pk=id)
        be = from_email_crud_registry.get(action.type, action.be_name)

        is_created = True

        if be:
            is_created = be.create_from_waiting_action_n_history(action)

        if is_created:
            action.delete()
        #else: Add a message for the user

    return {}
#    return HttpResponse()

@jsonify
@permission_required('crudity')
def reload(request, ct_id, waiting_type):
    ct = get_ct_or_404(ct_id)
    block = WaitingActionBlock(ct, waiting_type)

    ctx = RequestContext(request)
    ctx.update({'waiting_type_verbose': VERBOSE_CRUD, 'waiting_ct': ct, 'waiting_type': waiting_type}) #TODO: useful ?? (already set in the context by 'detailview_display')

    return [(block.id_, block.detailview_display(ctx))]
