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

from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required

from creme_core.views.generic import add_entity, view_entity_with_template, edit_entity
from creme_core.entities_access.functions_for_permissions import get_view_or_die, edit_object_or_die, delete_object_or_die

from projects.models import Project, ProjectTask
from projects.forms.task import TaskCreateForm, TaskEditForm


#TODO: inner popup ???
@login_required
@get_view_or_die('projects')
def add(request, project_id):
    """
        @Permissions : Acces or Admin to project app & Edit Project
    """
    project = get_object_or_404(Project, pk=project_id)

    die_status = edit_object_or_die(request, project)
    if die_status:
        return die_status

    return add_entity(request, TaskCreateForm, project.get_absolute_url(),
                      extra_initial={'project': project.id})

@login_required
@get_view_or_die('projects')
def detailview(request, object_id):
    """
        @Permissions : Acces or Admin to project app & implicit from view_entity_with_template
    """
    return view_entity_with_template(request, object_id, ProjectTask,
                                     '/projects/task',
                                     'projects/view_task.html')

@login_required
@get_view_or_die('projects')
def edit(request, task_id):
    """
        @Permissions : Acces or Admin to project & Edit on current object
    """
    return edit_entity(request, task_id, ProjectTask, TaskEditForm, 'projects')

@login_required
@get_view_or_die('projects')
def delete(request, task_id=None):
    """
        @Permissions : Acces or Admin to project app & Delete on current task object (pass but notify if it hasn't permission)
    """
    task = get_object_or_404(ProjectTask, pk=request.POST.get('id', task_id))
    project = task.project

    die_status = edit_object_or_die(request, project)
    if die_status:
        return die_status

    die_status = delete_object_or_die(request, task)
    if die_status:
        return die_status

    task.delete()

    if request.is_ajax():
        return HttpResponse()

    return HttpResponseRedirect(project.get_absolute_url())

@login_required
@get_view_or_die('projects')
def delete_parent(request):
    POST = request.POST
    task = get_object_or_404(ProjectTask, pk=POST.get('id'))
    project = task.project

    die_status = edit_object_or_die(request, project)
    if die_status:
        return die_status

    die_status = edit_object_or_die(request, task)
    if die_status:
        return die_status

    task.parents_task.remove(POST.get('parent_id'))

    return HttpResponse("")
