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

import datetime

from django.http import HttpResponseRedirect
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.decorators import login_required

from creme_core.views.generic import view_entity_with_template, add_entity, list_view, edit_entity
from creme_core.entities_access.functions_for_permissions import add_view_or_die, get_view_or_die, edit_object_or_die
from creme_core.gui.last_viewed import change_page_for_last_item_viewed

from projects.models import Project
from projects.forms.project import ProjectCreateForm, ProjectEditForm


@login_required
@get_view_or_die('projects')
@add_view_or_die(ContentType.objects.get_for_model(Project), None, 'projects')
def add(request):
    return add_entity(request, ProjectCreateForm)

def edit(request, project_id):
    return edit_entity(request, project_id, Project, ProjectEditForm, 'projects')

@login_required
@get_view_or_die('projects')
@change_page_for_last_item_viewed
def listview(request):
    return list_view(request, Project, extra_dict={'add_url':'/projects/project/add'})

@login_required
@get_view_or_die('projects')
def detailview(request, project_id):
    """
        @Permissions : Acces or Admin to project app & Read on current Project object
    """
    return view_entity_with_template(request, project_id, Project,
                                     '/projects/project',
                                     'projects/view_project.html',)

def close(request, project_id):
    project = Project.objects.get(pk=project_id)

    die_status = edit_object_or_die(request, project)

    if die_status:
        return die_status

    project.effective_end_date = datetime.date.today()
    project.save()

    return HttpResponseRedirect(project.get_absolute_url())
