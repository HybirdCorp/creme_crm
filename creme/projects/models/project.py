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

from django.db.models import CharField, TextField, ForeignKey, DateTimeField
from django.utils.translation import ugettext_lazy as _
from django.db.models import Max

from creme_core.models import CremeEntity, Relation

from projects.models import ProjectStatus
from projects.constants import REL_OBJ_PROJECT_MANAGER


class Project(CremeEntity):
    name                = CharField(_(u'Nom du projet'), max_length=100, blank=True, null=True)
    description         = TextField(_(u'Description du projet'), blank=True, null=True)
    status              = ForeignKey(ProjectStatus, verbose_name=_(u'Statut'))
    start_date          = DateTimeField(_(u'Début prévisionnel'), blank=True, null=True)
    end_date            = DateTimeField(_(u'Fin prévisionnel'), blank=True, null=True)
    effective_end_date  = DateTimeField(_(u'Fin effective'), blank=True, null=True)

    tasks_list          = None

    class Meta:
        app_label = 'projects'
        verbose_name = _(u'Projet')
        verbose_name_plural = _(u'Projets')

    def __unicode__(self) :
        return self.name

    def get_absolute_url(self):
        return "/projects/project/%s" % self.id

    def get_edit_absolute_url(self):
        return "/projects/project/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        return "/projects/projects"

    def get_delete_absolute_url(self):
        return "/projects/project/delete/%s" % self.id

    ##### ------------------ #####
    ##### Business functions #####
    ##### ------------------ #####

    def delete(self):
        for task in self.get_tasks():
            task.delete()
        super(Project, self).delete()

    def add_responsibles(self, responsibles_list):
        for responsible in responsibles_list:
            Relation.create(self, REL_OBJ_PROJECT_MANAGER, responsible)

    def get_tasks(self):
        if self.tasks_list is None:
            self.tasks_list = self.tasks_set.all()
        return self.tasks_list

    def attribute_order_task(self):
        max_order = self.get_tasks().aggregate(Max('order'))['order__max']
        return (max_order + 1) if max_order is not None else 1

    def get_project_cost(self):
        return sum(task.get_task_cost() for task in self.get_tasks())

    def get_expected_duration(self):
        return sum(task.duration for task in self.get_tasks())

    def get_effective_duration(self):
        return sum(task.get_effective_duration() for task in self.get_tasks())

    def get_delay(self):
        return sum(max(0, task.get_delay()) for task in self.get_tasks())
