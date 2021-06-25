# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2021  Hybird
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

from django.utils.translation import gettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class ProjectsConfig(CremeAppConfig):
    default = True
    name = 'creme.projects'
    verbose_name = _('Projects')
    dependencies = ['creme.persons', 'creme.activities']

    def all_apps_ready(self):
        from . import get_project_model, get_task_model

        self.Project     = get_project_model()
        self.ProjectTask = get_task_model()
        super().all_apps_ready()

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.Project, self.ProjectTask)

    def register_actions(self, actions_registry):
        from creme.projects import actions

        actions_registry.register_instance_actions(actions.ProjectCloseAction)

    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(
            bricks.ProjectExtraInfoBrick,
            bricks.TaskExtraInfoBrick,
            bricks.ProjectTasksBrick,
            bricks.TaskResourcesBrick,
            bricks.TaskActivitiesBrick,
            bricks.ParentTasksBrick,
        )

    def register_creme_config(self, config_registry):
        from . import models

        register_model = config_registry.register_model
        register_model(models.ProjectStatus, 'projectstatus')
        register_model(models.TaskStatus,    'taskstatus')

    def register_custom_forms(self, cform_registry):
        from . import custom_forms

        cform_registry.register(
            custom_forms.PROJECT_CREATION_CFORM,
            custom_forms.PROJECT_EDITION_CFORM,

            custom_forms.TASK_CREATION_CFORM,
            custom_forms.TASK_EDITION_CFORM,
        )

    def register_fields_config(self, fields_config_registry):
        fields_config_registry.register_models(
            self.Project,
            # TODO: self.ProjectTask ?
        )

    def register_icons(self, icon_registry):
        from .models import Resource

        icon_registry.register(
            self.Project, 'images/project_%(size)s.png',
        ).register(
            self.ProjectTask, 'images/task_%(size)s.png',
        ).register(
            Resource, 'images/task_%(size)s.png',
        )

    # def register_menu(self, creme_menu):
    #     Project = self.Project
    #     creme_menu.get(
    #         'features', 'tools',
    #     ).add(
    #         creme_menu.URLItem.list_view('projects-projects', model=Project),
    #         priority=50,
    #     )
    #     creme_menu.get(
    #         'creation', 'any_forms',
    #     ).get_or_create_group(
    #         'tools', label=_('Tools'), priority=100,
    #     ).add_link(
    #         'projects-create_project', Project, priority=50,
    #     )

    def register_menu_entries(self, menu_registry):
        from . import menu

        menu_registry.register(
            menu.ProjectsEntry,
            menu.ProjectCreationEntry,
        )

    def register_creation_menu(self, creation_menu_registry):
        creation_menu_registry.get_or_create_group(
            'tools', label=_('Tools'), priority=100,
        ).add_link(
            'projects-create_project', self.Project, priority=50,
        )
