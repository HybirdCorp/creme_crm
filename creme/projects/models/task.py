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

from itertools import chain

from django.db.models import ForeignKey, ManyToManyField, PositiveIntegerField, PROTECT
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.models.relation import Relation

from creme.activities.models import Activity
from creme.activities.constants import REL_SUB_PART_2_ACTIVITY, NARROW

from ..constants import COMPLETED_PK, CANCELED_PK
from .project import Project
from .taskstatus import TaskStatus


class ProjectTask(Activity):
    project      = ForeignKey(Project, verbose_name=_(u'Project'), related_name='tasks_set')
    order        = PositiveIntegerField(_(u'Order'), blank=True, null=True)
    parent_tasks = ManyToManyField("self", blank=True, null=True, symmetrical=False, related_name='children_set') #TODO: rename parent_tasks
#    duration     = PositiveIntegerField(_(u'Estimated duration (in hours)'), blank=False, null=False) #TODO delete this field ? already have activity duration in Activity
    tstatus      = ForeignKey(TaskStatus, verbose_name=_(u'Task situation'), on_delete=PROTECT)

    #header_filter_exclude_fields = Activity.header_filter_exclude_fields + ['activity_ptr'] #todo: use a set() ??
    #excluded_fields_in_html_output = Activity.excluded_fields_in_html_output + ['status']

    effective_duration = None
    resources          = None
    working_periods    = None
    parents            = None

    class Meta:
        app_label = 'projects'
        verbose_name = _(u'Task of project')
        verbose_name_plural = _(u'Tasks of project')

    def __init__ (self, *args , **kwargs):
        super(ProjectTask, self).__init__(*args, **kwargs)
        self.floating_type = NARROW

    def _pre_delete(self):
        for relation in Relation.objects.filter(type=REL_SUB_PART_2_ACTIVITY, object_entity=self):
            relation._delete_without_transaction()

    def get_absolute_url(self):
        return "/projects/task/%s" % self.id

    def get_edit_absolute_url(self):
        return "/projects/task/edit/%s" % self.id

    ##### ------------------ #####
    ##### Business functions #####
    ##### ------------------ #####

    def delete(self):
        for resource in self.get_resources():
            resource.delete()
        super(ProjectTask, self).delete()

    def get_parents(self):
        if self.parents is None:
            self.parents = self.parent_tasks.all()
        return self.parents

    def get_subtasks(self): #store result in a cache ?
        """Return all the subtasks in a list.
        Subtasks include the task itself, all its children, the children of its children etc...
        """
        subtasks = level_tasks = [self]

        #TODO: it would be cool if the django ORM allows us to write optimized queries for M2M ....
        while level_tasks:
            level_tasks = list(chain.from_iterable(task.children_set.all() for task in level_tasks))
            subtasks.extend(level_tasks)

        return subtasks

    def get_resources(self):
        if self.resources is None:
            self.resources = self.resources_set.all()
        return self.resources

    def get_working_periods(self):
        if self.working_periods is None:
            self.working_periods = self.tasks_set.all()
        return self.working_periods

    def get_task_cost(self):
        total = 0
        effective_duration = self.get_effective_duration()
        for res in self.get_resources():
            total += res.hourly_cost
        return total * effective_duration

    def get_effective_duration(self, format='h'):
        if self.effective_duration is None:
            self.effective_duration = sum(period.duration for period in self.get_working_periods())

        if format == '%':
            return (self.effective_duration * 100) / self.duration

        return self.effective_duration

    def get_delay(self):
        return self.get_effective_duration() - self.duration

    def is_alive(self):
        return self.tstatus_id not in (COMPLETED_PK, CANCELED_PK)

    def _clone_m2m(self, source):#Handled manually in clone_scope
        pass

    def _pre_save_clone(self, source):#Busy hasn't the same semantic here
        pass

    def _post_save_clone(self, source):
        for resource in source.get_resources():
            resource.clone_for_task(self)

        for working_period in source.get_working_periods():
            working_period.clone(self)

    @staticmethod
    def clone_scope(tasks, project):
        """Clone each task in 'tasks',assign them to 'project', and restore links between each task
        @params tasks : an iterable of ProjectTask
        @params project : A Project
        """
        context = {}

        project_task_filter = ProjectTask.objects.filter

        for task in tasks:
            new_task = task.clone()
            new_task.project = project
            new_task.save()

            context[task.id] = {'new_pk':     new_task.id, 
                                'o_children': project_task_filter(parent_tasks=task.id)
                                                .values_list('pk', flat=True),
                               }
#            context[new_task.id] = task.id

        new_links = dict((values['new_pk'], 
                          [context[old_child_id]['new_pk'] for old_child_id in values['o_children']]
                         ) for old_key, values in context.iteritems()
                        )

        for task in project_task_filter(pk__in=new_links.keys()):
            for sub_task in project_task_filter(pk__in=new_links[task.id]):
                sub_task.parent_tasks.add(task)
