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

from projects.models import ProjectTask, Resource, WorkingPeriod


class ProjectTaskBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('projects', 'project_tasks')
    dependencies  = (ProjectTask,)
    verbose_name  = _(u'Tasks of a project')
    template_name = 'projects/templatetags/block_tasks.html'

    def detailview_display(self, context):
        project = context['object']
        return self._render(self.get_block_template_context(context, project.get_tasks(),
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, project.pk),
                                                            ))

class ResourceTaskBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('projects', 'resources')
    dependencies  = (Resource,)
    verbose_name  = _(u'Resources assigned to a task')
    template_name = 'projects/templatetags/block_resources.html'

    def detailview_display(self, context):
        task = context['object']
        return self._render(self.get_block_template_context(context, task.get_resources(),
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, task.pk),
                                                            ))


class WorkingPeriodTaskBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('projects', 'working_periods')
    dependencies  = (WorkingPeriod,)
    verbose_name  = _(u'Working periods for this task')
    template_name = 'projects/templatetags/block_working_periods.html'

    def detailview_display(self, context):
        task = context['object']
        return self._render(self.get_block_template_context(context, task.get_working_periods(),
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, task.pk),
                                                            ))


tasks_block           = ProjectTaskBlock()
resources_block       = ResourceTaskBlock()
working_periods_block = WorkingPeriodTaskBlock()
