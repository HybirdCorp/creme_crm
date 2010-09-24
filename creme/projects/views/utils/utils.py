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

from django.utils.translation import ugettext as _
from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.contrib.auth.decorators import login_required

from creme_core.models.entity import CremeEntity
from creme_core.entities_access.functions_for_permissions import get_view_or_die, edit_object_or_die
from creme_core.views.generic import inner_popup

from projects import constants


def error_popup(request, message):
    return inner_popup(request, 'creme_core/generics/error.html',
                       {
                         'form':   None,
                         'error_message':  message,
                       },
                       is_valid=False,
                       context_instance=RequestContext(request))

#TODO: factorise get_real_entity()....
@login_required
@get_view_or_die('projects')
def _add_generic(request, form, task_id, title):
    task = get_object_or_404(CremeEntity, pk=task_id)

    die_status = edit_object_or_die(request, task)
    if die_status:
        return die_status

    current_status_id = task.get_real_entity().status_id
    if current_status_id == constants.COMPLETED_PK or current_status_id == constants.CANCELED_PK:
        state = task.get_real_entity().status.name
        return error_popup(request,
                           _(u"You can't add a resources or a working period to a task which has status <%s>") % state)

    if request.POST:
        form_obj = form(request.POST, initial={'related_task': task.get_real_entity()})

        if form_obj.is_valid():
            form_obj.save()
    else:
        form_obj = form(initial={'related_task': task.get_real_entity()})

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {
                         'form':   form_obj,
                         'title':  title,
                       },
                       is_valid=form_obj.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))

@login_required
@get_view_or_die('projects')
def _edit_generic(request, form, entity_id, model, title):
    entity = get_object_or_404(model, pk=entity_id)

    die_status = edit_object_or_die(request, entity.task)
    if die_status:
        return die_status

    if request.POST :
        form_obj = form(request.POST, instance=entity)

        if form_obj.is_valid():
            form_obj.save()
    else:
        form_obj = form(instance=entity)

    return inner_popup(request, 'creme_core/generics/blockform/edit_popup.html',
                       {
                         'form':   form_obj,
                         'object': entity.task,
                         'title':  title,
                       },
                       is_valid=form_obj.is_valid(),
                       context_instance=RequestContext(request))
