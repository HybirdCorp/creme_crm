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

from django.http import HttpResponseRedirect, Http404
from django.contrib.auth.decorators import login_required, permission_required

from creme_core.views.generic import view_entity_with_template, add_entity, list_view, edit_entity
from creme_core.gui.last_viewed import change_page_for_last_item_viewed

from projects.models import Project
from projects.forms.project import ProjectCreateForm, ProjectEditForm


@login_required
@permission_required('projects')
@permission_required('projects.add_project')
def add(request):
    return add_entity(request, ProjectCreateForm)

@login_required
@permission_required('projects')
def edit(request, project_id):
    return edit_entity(request, project_id, Project, ProjectEditForm)

@login_required
@permission_required('projects')
@change_page_for_last_item_viewed
def listview(request):
    return list_view(request, Project, extra_dict={'add_url': '/projects/project/add'})

@login_required
@permission_required('projects')
def detailview(request, project_id):
    return view_entity_with_template(request, project_id, Project,
                                     '/projects/project',
                                     'projects/view_project.html',)

@login_required
@permission_required('projects')
def close(request, project_id):
    if request.method != "POST":
        raise Http404('This view uses POST method')

    project = Project.objects.get(pk=project_id)

    project.can_change_or_die(request.user)

    if not project.close():
        raise Http404('Project is already closed: %s' % project)

    project.save()

    return HttpResponseRedirect(project.get_absolute_url())
