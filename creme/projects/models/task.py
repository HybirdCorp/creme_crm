################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

# import warnings
from itertools import chain

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from creme.creme_core.models import CREME_REPLACE, CremeEntity, Relation

from ..constants import (
    REL_OBJ_LINKED_2_PTASK,
    REL_SUB_PART_AS_RESOURCE,
    UUID_TSTATUS_CANCELED,
    UUID_TSTATUS_COMPLETED,
)
from .taskstatus import TaskStatus


class AbstractProjectTask(CremeEntity):
    title = models.CharField(_('Title'), max_length=100)
    linked_project = models.ForeignKey(
        settings.PROJECTS_PROJECT_MODEL,
        on_delete=models.CASCADE,
        verbose_name=_('Project'),
        related_name='tasks_set',
        editable=False,
    )

    order = models.PositiveIntegerField(_('Order'), editable=False)
    parent_tasks = models.ManyToManyField(
        'self', symmetrical=False, related_name='children', editable=False,
    )

    start = models.DateTimeField(_('Start'))
    end   = models.DateTimeField(_('End'))
    duration = models.PositiveIntegerField(_('Duration (in hours)'), default=0)

    # TODO: rename "status" (does not collide with activity's status anymore)
    #       beware: data-migration for HeaderFilter, CustomFormConfigItem,
    #               SearchConfigItem, Bricks... is needed.
    tstatus = models.ForeignKey(
        TaskStatus, verbose_name=_('Task situation'), on_delete=CREME_REPLACE,
    )

    _DELETABLE_INTERNAL_RTYPE_IDS = (REL_OBJ_LINKED_2_PTASK,)

    creation_label = _('Create a task')
    save_label     = _('Save the task')

    class Meta:
        abstract = True
        app_label = 'projects'
        verbose_name = _('Task of project')
        verbose_name_plural = _('Tasks of project')
        ordering = ('-start',)

    effective_duration = None
    resources = None
    parents = None

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('projects__view_task', args=(self.id,))

    def get_edit_absolute_url(self):
        return reverse('projects__edit_task', args=(self.id,))

    def get_related_entity(self):
        return self.linked_project

    def get_parents(self):
        if self.parents is None:
            self.parents = self.parent_tasks.all()

        return self.parents

    def get_subtasks(self):  # TODO: store result in a cache ?
        """Return all the sub-tasks in a list.
        Sub-tasks include the task itself, all its children, the children of its children etc...
        """
        subtasks = level_tasks = [self]

        # TODO: use prefetch_related() ??
        while level_tasks:
            level_tasks = [
                *chain.from_iterable(task.children.all() for task in level_tasks),
            ]
            subtasks.extend(level_tasks)

        return subtasks

    def get_resources(self):
        if self.resources is None:
            self.resources = self.resources_set.select_related('linked_contact')

        return self.resources

    @property
    def related_activities(self):
        activities = [
            r.real_object
            for r in self.get_relations(REL_OBJ_LINKED_2_PTASK, real_obj_entities=True)
        ]
        resource_per_contactid = {r.linked_contact_id: r for r in self.get_resources()}
        contact_ids = dict(
            Relation.objects.filter(
                type=REL_SUB_PART_AS_RESOURCE,
                object_entity__in=[a.id for a in activities],
            ).values_list('object_entity_id', 'subject_entity_id')
        )

        for activity in activities:
            activity.projects_resource = resource_per_contactid[contact_ids[activity.id]]

        return activities

    # TODO: property
    def get_task_cost(self):
        return sum(
            (activity.duration or 0) * activity.projects_resource.hourly_cost
            for activity in self.related_activities
        )

    def get_effective_duration(self, format='h'):
        if self.effective_duration is None:
            self.effective_duration = sum(
                activity.duration or 0
                for activity in self.related_activities
            )

        if format == '%':
            duration = self.duration

            return (self.effective_duration * 100) / duration if duration else 100

        return self.effective_duration

    # TODO: property
    def get_delay(self):
        return self.get_effective_duration() - self.duration

    # TODO: property
    def is_alive(self):
        # TODO: boolean field if TaskStatus instead?
        return str(self.tstatus.uuid) not in (UUID_TSTATUS_COMPLETED, UUID_TSTATUS_CANCELED)

    # def _clone_m2m(self, source):  # Handled manually in clone_scope
    #     warnings.warn(
    #         'The method ProjectTask._clone_m2m() is deprecated.',
    #         DeprecationWarning,
    #     )
    #
    # def _post_save_clone(self, source):
    #     warnings.warn(
    #         'The method ProjectTask._post_save_clone() is deprecated.',
    #         DeprecationWarning,
    #     )
    #
    #     for resource in source.get_resources():
    #         resource.clone_for_task(self)

    # @classmethod
    # def clone_scope(cls, tasks, project):
    #     """Clone each task in 'tasks', assign them to 'project',
    #     and restore links between each task.
    #     @params tasks: an iterable of ProjectTask.
    #     @params project: a Project instance.
    #     """
    #     warnings.warn(
    #         'The method ProjectTask.clone_scope() is deprecated.',
    #         DeprecationWarning,
    #     )
    #
    #     context = {}
    #
    #     project_task_filter = cls._default_manager.filter
    #
    #     for task in tasks:
    #         new_task = task.clone()
    #         new_task.linked_project = project
    #         new_task.save()
    #
    #         context[task.id] = {
    #             'new_pk':     new_task.id,
    #             'o_children': project_task_filter(
    #                 parent_tasks=task.id,
    #             ).values_list('pk', flat=True),
    #         }
    #
    #     new_links = {
    #         values['new_pk']: [
    #             context[old_child_id]['new_pk']
    #             for old_child_id in values['o_children']
    #         ]
    #         for values in context.values()
    #     }
    #
    #     for task in project_task_filter(pk__in=new_links.keys()):
    #         for sub_task in project_task_filter(pk__in=new_links[task.id]):
    #             sub_task.parent_tasks.add(task)

    def save(self, *args, **kwargs):
        if self.pk is None and not self.order:
            self.order = self.linked_project.attribute_order_task()

        super().save(*args, **kwargs)


class ProjectTask(AbstractProjectTask):
    class Meta(AbstractProjectTask.Meta):
        swappable = 'PROJECTS_TASK_MODEL'
