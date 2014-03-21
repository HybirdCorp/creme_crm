# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext as _

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views.generic import (add_to_entity, view_entity,
        edit_entity, edit_model_with_popup)

from ..forms.task import TaskCreateForm, TaskEditForm, TaskAddParentForm
from ..models import Project, ProjectTask


@login_required
@permission_required('projects.add_projecttask')
def add(request, project_id):
    return add_to_entity(request, project_id, TaskCreateForm,
                         _(u'Add a task to <%s>'), entity_class=Project,
                        )

@login_required
@permission_required('projects')
def detailview(request, object_id):
    return view_entity(request, object_id, ProjectTask, '/projects/task', 'projects/view_task.html')

@login_required
@permission_required('projects')
def edit(request, task_id):
    return edit_entity(request, task_id, ProjectTask, TaskEditForm)

@login_required
@permission_required('projects')
def edit_popup(request, task_id):
    return edit_model_with_popup(request, {'pk': task_id}, ProjectTask, TaskEditForm)

@login_required
@permission_required('projects')
def add_parent(request, task_id):
    return edit_model_with_popup(request, {'pk': task_id}, ProjectTask, TaskAddParentForm)

@login_required
@permission_required('projects')
def delete(request):
    task = get_object_or_404(ProjectTask, pk=request.POST.get('id'))
    project = task.project
    user = request.user

    user.has_perm_to_change_or_die(project)
    user.has_perm_to_delete_or_die(task)

    task.delete()

    if request.is_ajax():
        return HttpResponse()

    return redirect(project)

@login_required
@permission_required('projects')
def delete_parent(request):
    POST = request.POST
    parent_id = get_from_POST_or_404(POST, 'parent_id')
    task = get_object_or_404(ProjectTask, pk=get_from_POST_or_404(POST, 'id'))
    user = request.user

    #user.has_perm_to_change_or_die(task.project) #beware: modify block_tasks.html template if uncommented....
    user.has_perm_to_change_or_die(task)

    task.parent_tasks.remove(parent_id)

    return HttpResponse("")
