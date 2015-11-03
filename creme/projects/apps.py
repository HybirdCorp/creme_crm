# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015  Hybird
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

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class ProjectsConfig(CremeAppConfig):
    name = 'creme.projects'
    verbose_name = _(u'Projects')
    dependencies = ['creme.persons', 'creme.activities']

#    def ready(self):
    def all_apps_ready(self):
        from . import get_project_model, get_task_model

        self.Project     = get_project_model()
        self.ProjectTask = get_task_model()
#        super(ProjectsConfig, self).ready()
        super(ProjectsConfig, self).all_apps_ready()

    def register_creme_app(self, creme_registry):
        creme_registry.register_app('projects', _(u'Projects'), '/projects')

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.Project, self.ProjectTask)

    def register_blocks(self, block_registry):
        from .blocks import block_list

        block_registry.register(*block_list)

    def register_icons(self, icon_registry):
        from .models import Resource

        reg_icon = icon_registry.register
        reg_icon(self.Project,     'images/project_%(size)s.png')
        reg_icon(self.ProjectTask, 'images/task_%(size)s.png')
        reg_icon(Resource,         'images/task_%(size)s.png')

    def register_menu(self, creme_menu):
        from django.core.urlresolvers import reverse_lazy as reverse

        from creme.creme_core.auth import build_creation_perm

        Project = self.Project
        reg_item = creme_menu.register_app('projects', '/projects/').register_item
        reg_item('/projects/',                        _('Portal of projects'), 'projects')
        reg_item(reverse('projects__list_projects'),  _('All projects'),       'projects')
        reg_item(reverse('projects__create_project'), Project.creation_label,  build_creation_perm(Project))
