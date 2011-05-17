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

from django.db.models import ForeignKey, PositiveIntegerField, DateTimeField
from django.utils.translation import ugettext_lazy as _

from creme_core.models import CremeModel

from resource import Resource
from task import ProjectTask


class WorkingPeriod(CremeModel):
    start_date = DateTimeField(_(u'Between'), blank=True, null=True)
    end_date   = DateTimeField(_(u'And'), blank=True, null=True)
    duration   = PositiveIntegerField(_(u"Duration (in hours)"), blank=True, null=True)
    task       = ForeignKey(ProjectTask, verbose_name=_(u'Task'), related_name='tasks_set')
    resource   = ForeignKey(Resource, verbose_name=_(u'Resource'))

    class Meta:
        app_label = 'projects'
        verbose_name = _(u'Working period')
        verbose_name_plural = _(u'Working periods')

    def __unicode__(self):
        return u'%s %s' % (self.start_date, self.end_date)

    def get_edit_absolute_url(self):
        return "/projects/period/edit/%s" % self.id

    def clone(self, task):
        return WorkingPeriod.objects.create(start_date=self.start_date,
                                            end_date=self.end_date,
                                            duration=self.duration,
                                            task=task,
                                            resource=self.resource)