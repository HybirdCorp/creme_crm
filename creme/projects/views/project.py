# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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

from django.core.urlresolvers import reverse
from django.http import Http404
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views.decorators import POST_only
from creme.creme_core.views.generic import view_entity, add_entity, list_view, edit_entity

from .. import get_project_model
from ..constants import DEFAULT_HFILTER_PROJECT
from ..forms.project import ProjectCreateForm, ProjectEditForm
from ..models import ProjectStatus # Project


Project = get_project_model()


def abstract_add_project(request, form=ProjectCreateForm,
                         submit_label=_('Save the project'),
                        ):
    return add_entity(request, form,
                      extra_initial={'status': ProjectStatus.objects.first()},
                      extra_template_dict={'submit_label': submit_label},
                     )


def abstract_edit_project(request, project_id, form=ProjectEditForm):
    return edit_entity(request, project_id, Project, form)


def abstract_view_project(request, project_id,
                          template='projects/view_project.html',
                         ):
    return view_entity(request, project_id, Project, template=template,
                       # path='/projects/project',
                      )


@login_required
# @permission_required(('projects', 'projects.add_project'))
@permission_required(('projects', cperm(Project)))
def add(request):
    return abstract_add_project(request)


@login_required
@permission_required('projects')
def edit(request, project_id):
    return abstract_edit_project(request, project_id)


@login_required
@permission_required('projects')
def listview(request):
    return list_view(request, Project, hf_pk=DEFAULT_HFILTER_PROJECT,
                     # extra_dict={'add_url': '/projects/project/add'},
                     # extra_dict={'add_url': reverse('projects__create_project')},
                    )


@login_required
@permission_required('projects')
def detailview(request, project_id):
    return abstract_view_project(request, project_id)


@login_required
@POST_only
@permission_required('projects')
def close(request, project_id):
    project = Project.objects.get(pk=project_id)

    request.user.has_perm_to_change_or_die(project)

    if not project.close():
        raise Http404('Project is already closed: %s' % project)

    project.save()

    return redirect(project)
