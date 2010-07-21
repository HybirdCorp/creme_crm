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

from django.utils.translation import ugettext_lazy as _

from creme_core.gui.block import QuerysetBlock


class ProjectTaskBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('projects', 'project_task')
    verbose_name  = _(u'Liste des tâches du projet')
    template_name = 'projects/templatetags/block_tasks.html'

    def detailview_display(self, context):
        project = context['object']
        return self._render(self.get_block_template_context(context, project.get_tasks(),
                                                            update_url='/projects/project/%s/tasks/reload/' % project.pk))

class ResourceTaskBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('projects', 'resource')
    verbose_name  = _(u'Ressource(s) affectée(s) à la tâche')
    template_name = 'projects/templatetags/block_resources.html'

    def detailview_display(self, context):
        task    = context['object']
        return self._render(self.get_block_template_context(context, task.get_resources(),
                                                            update_url='/projects/task/%s/resources/reload/' % task.pk))


class WorkingPeriodTaskBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('projects', 'working_period')
    verbose_name  = _(u'Période(s) travaillée(s) sur cette tâche')
    template_name = 'projects/templatetags/block_working_periods.html'

    def detailview_display(self, context):
        task    = context['object']
        return self._render(self.get_block_template_context(context, task.get_working_periods(),
                                                            update_url='/projects/task/%s/periods/reload/' % task.pk))


tasks_block           = ProjectTaskBlock()
resources_block       = ResourceTaskBlock()
working_periods_block = WorkingPeriodTaskBlock()
