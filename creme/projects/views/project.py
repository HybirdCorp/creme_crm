# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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
from django.shortcuts import redirect
from django.utils.translation import gettext as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.views import generic

from .. import custom_forms, get_project_model
from ..constants import DEFAULT_HFILTER_PROJECT
from ..models import ProjectStatus

Project = get_project_model()


class ProjectClosure(generic.base.EntityRelatedMixin, generic.CheckedView):
    permissions = 'projects'
    entity_id_url_kwarg = 'project_id'
    entity_classes = Project
    entity_select_for_update = True

    @atomic
    def post(self, *args, **kwargs):
        project = self.get_related_entity()

        if not project.close():
            raise ConflictError(_('Project is already closed.'))

        project.save()

        # TODO: if Ajax...
        return redirect(project)


class ProjectCreation(generic.EntityCreation):
    model = Project
    form_class = custom_forms.PROJECT_CREATION_CFORM

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
    form_class = custom_forms.PROJECT_EDITION_CFORM
    pk_url_kwarg = 'project_id'


class ProjectsList(generic.EntitiesList):
    model = Project
    default_headerfilter_id = DEFAULT_HFILTER_PROJECT
