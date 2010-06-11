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

from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import get_object_or_404

from django.contrib.auth.decorators import login_required

from creme_core.utils import jsonify

from creme_core.models import CremeEntity
from creme_core.gui.block import str2list

from assistants.models import Action
from assistants.forms.action import ActionCreateForm, ActionEditForm
from assistants.blocks import actions_it_block, actions_nit_block
from utils import generic_add, generic_edit, generic_post_delete


def add(request, entity_id):
    return generic_add(request, entity_id, ActionCreateForm, u'Nouvelle action pour <%s>')

def edit(request, action_id):
    return generic_edit(request, action_id, Action, ActionEditForm, u"Action pour <%s>")

#def delete(request, action_id):
def delete(request):
#    return generic_delete(request, request.POST.get('id'), Action)
    return generic_post_delete(request, Action)

@login_required
def validate(request, action_id):
    action = get_object_or_404(Action, pk=action_id)
    action.is_ok = True
    action.validation_date = datetime.today()
    action.save()
    return HttpResponseRedirect(action.creme_entity.get_absolute_url())



@login_required
@jsonify ##
def reload_detailview(request, entity_id): #TODO: move into block methods ?????
    context = {'request': request, 'object': CremeEntity.objects.get(id=entity_id), 'today': datetime.today()}
    return [
            (actions_it_block.id_, actions_it_block.detailview_display(context)),
            (actions_nit_block.id_, actions_nit_block.detailview_display(context)),
           ]

@login_required
@jsonify ##
def reload_home(request):
    context = {'request': request, 'today': datetime.today()}
    return [
            (actions_it_block.id_, actions_it_block.home_display(context)),
            (actions_nit_block.id_, actions_nit_block.home_display(context)),
           ]

@login_required
@jsonify ##
def reload_portal(request, ct_ids):
    context = {'request': request, 'today': datetime.today()}
    ct_ids = str2list(ct_ids)
    return [
            (actions_it_block.id_, actions_it_block.portal_display(context, ct_ids)),
            (actions_nit_block.id_, actions_nit_block.portal_display(context, ct_ids)),
           ]
