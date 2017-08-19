# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2017  Hybird
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
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.gui.bricks import SimpleBrick, PaginatedBrick, QuerysetBrick
from creme.creme_core.models import Relation

from creme.activities import get_activity_model

from creme import projects
from .constants import REL_OBJ_LINKED_2_PTASK
from .models import Resource


Activity = get_activity_model()

Project     = projects.get_project_model()
ProjectTask = projects.get_task_model()


class ProjectExtraInfoBrick(SimpleBrick):
    id_           = SimpleBrick.generate_id('projects', 'project_extra_info')
    dependencies  = (ProjectTask,)
    verbose_name  = _(u'Extra project information')
    # template_name = 'projects/templatetags/block_project_extra_info.html'
    template_name = 'projects/bricks/project-extra-info.html'
    target_ctypes = (Project,)


class TaskExtraInfoBrick(SimpleBrick):
    id_           = SimpleBrick.generate_id('projects', 'task_extra_info')
    dependencies  = (Activity,)
    verbose_name  = _(u'Extra project task information')
    # template_name = 'projects/templatetags/block_task_extra_info.html'
    template_name = 'projects/bricks/task-extra-info.html'
    target_ctypes = (ProjectTask,)


class ParentTasksBrick(QuerysetBrick):
    id_           = QuerysetBrick.generate_id('projects', 'parent_tasks')
    dependencies  = (ProjectTask,)
    verbose_name  = _(u'Parents of a task')
    # template_name = 'projects/templatetags/block_parent_tasks.html'
    template_name = 'projects/bricks/parent-tasks.html'
    target_ctypes = (ProjectTask,)

    def detailview_display(self, context):
        task = context['object']

        return self._render(self.get_template_context(
                    context,
                    task.parent_tasks.all(),
                    # update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, task.pk),
                    update_url=reverse('creme_core__reload_detailview_blocks', args=(self.id_, task.pk)),
        ))


class ProjectTasksBrick(QuerysetBrick):
    id_           = QuerysetBrick.generate_id('projects', 'project_tasks')
    dependencies  = (ProjectTask,)
    verbose_name  = _(u'Tasks of a project')
    # template_name = 'projects/templatetags/block_tasks.html'
    template_name = 'projects/bricks/tasks.html'
    target_ctypes = (Project,)

    def detailview_display(self, context):
        project = context['object']
        user    = context['user']
        creation_perm = user.has_perm(cperm(ProjectTask)) and user.has_perm_to_change(project)

        return self._render(self.get_template_context(
                    context, project.get_tasks(),
                    # update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, project.pk),
                    update_url=reverse('creme_core__reload_detailview_blocks', args=(self.id_, project.id)),
                    creation_perm=creation_perm,  # TODO: use a tempatetag instead ??
        ))


class TaskResourcesBrick(QuerysetBrick):
    id_           = QuerysetBrick.generate_id('projects', 'resources')
    dependencies  = (Resource,)
    verbose_name  = _(u'Resources assigned to a task')
    # template_name = 'projects/templatetags/block_resources.html'
    template_name = 'projects/bricks/resources.html'
    target_ctypes = (ProjectTask,)

    def detailview_display(self, context):
        task = context['object']

        return self._render(self.get_template_context(
                    context,
                    task.get_resources().select_related('linked_contact'),
                    # update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, task.pk),
                    update_url=reverse('creme_core__reload_detailview_blocks', args=(self.id_, task.pk)),
        ))


class TaskActivitiesBrick(PaginatedBrick):
    id_           = QuerysetBrick.generate_id('projects', 'task_activities')
    dependencies  = (Activity, Resource, Relation)
    relation_type_deps = (REL_OBJ_LINKED_2_PTASK, )
    verbose_name  = _(u'Activities for this task')
    # template_name = 'projects/templatetags/block_activities.html'
    template_name = 'projects/bricks/activities.html'
    target_ctypes = (ProjectTask,)

    def detailview_display(self, context):
        task = context['object']
        return self._render(self.get_template_context(
                    context,
                    task.related_activities,
                    # update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, task.pk),
                    update_url=reverse('creme_core__reload_detailview_blocks', args=(self.id_, task.pk)),
        ))
