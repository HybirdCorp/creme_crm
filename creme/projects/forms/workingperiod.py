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

from django.forms import IntegerField , DateTimeField
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.forms import CremeModelForm
from creme.creme_core.forms.fields import CreatorEntityField
from creme.creme_core.forms.widgets import DateTimeWidget

from ..models import WorkingPeriod, Resource
from ..constants import NOT_STARTED_PK, IN_PROGRESS_PK


class WorkingPeriodForm(CremeModelForm):
    resource   = CreatorEntityField(label=_(u'Resources allocated to this task'), required=True, model=Resource)
    start_date = DateTimeField(label=_(u'Between'), widget=DateTimeWidget(), required=False)
    end_date   = DateTimeField(label=_(u'And'), widget=DateTimeWidget(), required=False)
    duration   = IntegerField(label=_(u'Period duration'), required=True)

    class Meta:
        model = WorkingPeriod
        exclude = ['task']

    def __init__(self, task, *args, **kwargs):
        super(WorkingPeriodForm, self).__init__(*args, **kwargs)
        self.task = task

        self.fields['resource'].q_filter = {'task': task.pk}

    def save(self, *args, **kwargs):
        task = self.task
        self.instance.task = task

        if task.tstatus_id == NOT_STARTED_PK:
            task.tstatus_id = IN_PROGRESS_PK
            task.save()

        return super(WorkingPeriodForm, self).save(*args, **kwargs)
