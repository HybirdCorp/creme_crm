################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024  Hybird
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

from creme.creme_core.core import copying
from creme.creme_core.core.cloning import EntityCloner
from creme.creme_core.utils.collections import FluentList


class ChildTaskClonerM2MCopier(copying.ManyToManyFieldsCopier):
    # NB: Parenting is managed by TasksCopier
    #     & we do not want to mark the field as <clonable=False>.
    exclude = ['parent_tasks']


class ChildTaskResourcesCopier(copying.PostSaveCopier):
    def copy_to(self, target):
        for resource in self._source.get_resources():
            # TODO: remove method & move its code here?
            resource.clone_for_task(task=target)


class ChildTaskCloner(EntityCloner):
    post_save_copiers = FluentList(
        EntityCloner.post_save_copiers
    ).replace(
        old=copying.ManyToManyFieldsCopier, new=ChildTaskClonerM2MCopier,
    ).append(ChildTaskResourcesCopier)

    def __init__(self, project):
        super().__init__()
        self.project = project

    def _pre_save(self, *, user, source, target):
        super()._pre_save(user=user, source=source, target=target)
        target.linked_project = self.project


class TasksCopier(copying.PostSaveCopier):
    task_cloner_class = ChildTaskCloner

    def copy_to(self, target):
        from creme.projects.models.task import ProjectTask

        context = {}
        project_task_filter = ProjectTask._default_manager.filter
        task_cloner = self.task_cloner_class(project=target)
        user = self._user

        for task in self._source.get_tasks():
            cloned_task = task_cloner.perform(user=user, entity=task)
            context[task.id] = {
                'new_pk':     cloned_task.id,
                'o_children': project_task_filter(
                    parent_tasks=task.id,
                ).values_list('pk', flat=True),
            }

        new_links = {
            values['new_pk']: [
                context[old_child_id]['new_pk']
                for old_child_id in values['o_children']
            ]
            for values in context.values()
        }

        for task in project_task_filter(pk__in=new_links.keys()):
            for sub_task in project_task_filter(pk__in=new_links[task.id]):
                sub_task.parent_tasks.add(task)


class ProjectCloner(EntityCloner):
    post_save_copiers = [
        *EntityCloner.post_save_copiers,
        TasksCopier,
    ]
