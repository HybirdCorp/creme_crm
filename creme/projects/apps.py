# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2018  Hybird
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

    def all_apps_ready(self):
        from . import get_project_model, get_task_model

        self.Project     = get_project_model()
        self.ProjectTask = get_task_model()
        super(ProjectsConfig, self).all_apps_ready()

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.Project, self.ProjectTask)

    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(bricks.ProjectExtraInfoBrick,
                                bricks.TaskExtraInfoBrick,
                                bricks.ProjectTasksBrick,
                                bricks.TaskResourcesBrick,
                                bricks.TaskActivitiesBrick,
                                bricks.ParentTasksBrick,
                               )

    def register_icons(self, icon_registry):
        from .models import Resource

        reg_icon = icon_registry.register
        reg_icon(self.Project,     'images/project_%(size)s.png')
        reg_icon(self.ProjectTask, 'images/task_%(size)s.png')
        reg_icon(Resource,         'images/task_%(size)s.png')

    def register_menu(self, creme_menu):
        from django.conf import settings

        Project = self.Project

        if settings.OLD_MENU:
            from django.core.urlresolvers import reverse_lazy as reverse
            from creme.creme_core.auth import build_creation_perm

            reg_item = creme_menu.register_app('projects', '/projects/').register_item
            reg_item(reverse('projects__portal'),         _('Portal of projects'), 'projects')
            reg_item(reverse('projects__list_projects'),  _('All projects'),       'projects')
            reg_item(reverse('projects__create_project'), Project.creation_label,  build_creation_perm(Project))
        else:
            creme_menu.get('features', 'tools') \
                      .add(creme_menu.URLItem.list_view('projects-projects', model=Project), priority=50)
            creme_menu.get('creation', 'any_forms') \
                      .get_or_create_group('tools', label=_(u'Tools'), priority=100) \
                      .add_link('projects-create_project', Project, priority=50)
