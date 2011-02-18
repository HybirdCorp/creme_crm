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

from django.db.models import ForeignKey, ManyToManyField, PositiveIntegerField
from django.utils.translation import ugettext_lazy as _

from activities.models import Activity, ActivityType
from activities.constants import ACTIVITYTYPE_TASK

from projects import constants
from project import Project
from taskstatus import TaskStatus


class ProjectTask(Activity):
    project      = ForeignKey(Project, verbose_name=_(u'Project'), related_name='tasks_set')
    order        = PositiveIntegerField(_(u'Order'), blank=True, null=True)
    parents_task = ManyToManyField("self", blank=True, null=True, symmetrical=False)
    duration     = PositiveIntegerField(_(u'Estimated duration (in hours)'), blank=False, null=False)
    tstatus      = ForeignKey(TaskStatus, verbose_name=_(u'Status'))

    header_filter_exclude_fields = Activity.header_filter_exclude_fields + ['activity_ptr'] #TODO: use a set() ??
    excluded_fields_in_html_output = Activity.excluded_fields_in_html_output + ['status']

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
        self.type_id = ACTIVITYTYPE_TASK

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
            self.parents = self.parents_task.all()
        return self.parents

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
        return self.tstatus_id not in (constants.COMPLETED_PK, constants.CANCELED_PK)
