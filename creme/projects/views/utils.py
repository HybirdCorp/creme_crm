# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from creme.creme_core.views.generic import inner_popup

from creme.projects.models import ProjectTask


def error_popup(request, message):
    return inner_popup(request, 'creme_core/generics/error.html',
                       {'form':           None,
                        'error_message':  message,
                       },
                       is_valid=False,
                      )

#TODO: improve add_to_entity (see:"if not task.is_alive() etc...") ???
def _add_generic(request, form, task_id, title):
    task = get_object_or_404(ProjectTask, pk=task_id)
    user = request.user

    task.can_change_or_die(user)

    if not task.is_alive():
        state = task.tstatus.name
        return error_popup(request,
                           _(u"You can't add a resources or a working period to a task which has status <%s>") % state)

    if request.method == 'POST':
        form_obj = form(task, user=user, data=request.POST)

        if form_obj.is_valid():
            form_obj.save()
    else:
        form_obj = form(task, user=user)

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {'form':   form_obj,
                         'title':  title,
                       },
                       is_valid=form_obj.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )

#TODO: remove and use generic.edit_related_to_entity() ??
def _edit_generic(request, form, obj_id, model, title):
    obj  = get_object_or_404(model, pk=obj_id)
    task = obj.task
    user = request.user

    task.can_change_or_die(user)

    if request.method == 'POST':
        form_obj = form(task, user=user, data=request.POST, instance=obj)

        if form_obj.is_valid():
            form_obj.save()
    else:
        form_obj = form(task, user=user, instance=obj)

    return inner_popup(request, 'creme_core/generics/blockform/edit_popup.html',
                       {'form':   form_obj,
                         'object': task, #TODO: useful ???
                         'title':  title,
                       },
                       is_valid=form_obj.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )
