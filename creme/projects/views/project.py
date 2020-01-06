# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

from django.db.transaction import atomic
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views.decorators import POST_only
from creme.creme_core.views import generic

from .. import get_project_model
from ..constants import DEFAULT_HFILTER_PROJECT
from ..forms import project as project_forms
from ..models import ProjectStatus

Project = get_project_model()


@login_required
@POST_only
@permission_required('projects')
@atomic
def close(request, project_id):
    project = get_object_or_404(Project.objects.select_for_update(), id=project_id)

    request.user.has_perm_to_change_or_die(project)

    if not project.close():
        raise Http404('Project is already closed: {}'.format(project))

    project.save()

    return redirect(project)


class ProjectCreation(generic.EntityCreation):
    model = Project
    form_class = project_forms.ProjectCreateForm

    def get_initial(self):
        initial = super().get_initial()
        initial['status'] = ProjectStatus.objects.first()

        return initial


class ProjectDetail(generic.EntityDetail):
    model = Project
    template_name = 'projects/view_project.html'
    pk_url_kwarg = 'project_id'


class ProjectEdition(generic.EntityEdition):
    model = Project
    form_class = project_forms.ProjectEditForm
    pk_url_kwarg = 'project_id'


class ProjectsList(generic.EntitiesList):
    model = Project
    default_headerfilter_id = DEFAULT_HFILTER_PROJECT
