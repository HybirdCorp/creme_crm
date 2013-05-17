# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

#from creme.creme_core.models import CremeEntity
from creme.creme_core.gui.block import SimpleBlock, QuerysetBlock

from .models import Project, ProjectTask, Resource, WorkingPeriod


class ProjectExtraInfo(SimpleBlock):
    id_           = SimpleBlock.generate_id('projects', 'project_extra_info')
    dependencies  = (ProjectTask,)
    verbose_name  = _(u'Extra project information')
    template_name = 'projects/templatetags/block_project_extra_info.html'
    target_ctypes = (Project,)


class TaskExtraInfo(SimpleBlock):
    id_           = SimpleBlock.generate_id('projects', 'task_extra_info')
    dependencies  = (WorkingPeriod,)
    verbose_name  = _(u'Extra project task information')
    template_name = 'projects/templatetags/block_task_extra_info.html'
    target_ctypes = (ProjectTask,)

    #def detailview_display(self, context):
        #return self._render(self.get_block_template_context(context)) #todo: move to Block.detailview_display() ??


class ParentTasksBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('projects', 'parent_tasks')
    dependencies  = (ProjectTask,)
    verbose_name  = _(u'Parents of a Task')
    template_name = 'projects/templatetags/block_parent_tasks.html'
    target_ctypes = (ProjectTask,)

    def detailview_display(self, context):
        task = context['object']
        btc = self.get_block_template_context(context,
                                              task.parent_tasks.all(),
                                              update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, task.pk),
                                             )

        #CremeEntity.populate_credentials(btc['page'].object_list, context['user'])

        return self._render(btc)


class ProjectTasksBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('projects', 'project_tasks')
    dependencies  = (ProjectTask,)
    verbose_name  = _(u'Tasks of a project')
    template_name = 'projects/templatetags/block_tasks.html'
    target_ctypes = (Project,)

    def detailview_display(self, context):
        project = context['object']
        user    = context['user']
        creation_perm = user.has_perm('projects.add_projecttask') and user.has_perm_to_change(project)
        btc = self.get_block_template_context(context, project.get_tasks(),
                                              update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, project.pk),
                                              creation_perm=creation_perm, #TODO: use a tempatetag instead ??
                                             )

        #CremeEntity.populate_credentials(btc['page'].object_list, user)

        return self._render(btc)


class TaskResourcesBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('projects', 'resources')
    dependencies  = (Resource, WorkingPeriod) #NB: deleting a Resource -> delete all related WorkingPeriods
    verbose_name  = _(u'Resources assigned to a task')
    template_name = 'projects/templatetags/block_resources.html'
    target_ctypes = (ProjectTask,)

    def detailview_display(self, context):
        task = context['object']
        btc = self.get_block_template_context(context,
                                              task.get_resources().select_related('linked_contact'),
                                              update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, task.pk),
                                             )

        #CremeEntity.populate_credentials([r.linked_contact for r in  btc['page'].object_list],
                                         #context['user']
                                        #)

        return self._render(btc)


class TaskWorkingPeriodsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('projects', 'working_periods')
    dependencies  = (WorkingPeriod,)
    verbose_name  = _(u'Working periods for this task')
    template_name = 'projects/templatetags/block_working_periods.html'
    target_ctypes = (ProjectTask,)

    def detailview_display(self, context):
        task = context['object']
        return self._render(self.get_block_template_context(context, task.get_working_periods(),
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, task.pk),
                                                            ))


project_extra_info        = ProjectExtraInfo()
task_extra_info           = TaskExtraInfo()
project_tasks_block       = ProjectTasksBlock()
task_resources_block      = TaskResourcesBlock()
task_workingperiods_block = TaskWorkingPeriodsBlock()
parent_tasks_block        = ParentTasksBlock()

block_list = (
        project_extra_info,
        task_extra_info,
        project_tasks_block,
        task_resources_block,
        task_workingperiods_block,
        parent_tasks_block,
    )