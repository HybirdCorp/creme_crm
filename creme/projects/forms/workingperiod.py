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

from django.forms import IntegerField , DateTimeField, ValidationError
from django.utils.translation import ugettext_lazy as _

from creme_core.forms import CremeModelForm
from creme_core.forms.fields import CremeEntityField
from creme_core.forms.widgets import DateTimeWidget

from projects.models import WorkingPeriod, Resource, TaskStatus
from projects import constants


class PeriodEditForm(CremeModelForm):
    resource   = CremeEntityField(label=_(u'Resources allocated to this task'), required=True, model=Resource)
    start_date = DateTimeField(label=_(u'Between'), widget=DateTimeWidget(), required=False)
    end_date   = DateTimeField(label=_(u'And'), widget=DateTimeWidget(), required=False)
    duration   = IntegerField(label=_(u'Period duration'), required=True)

    class Meta:
        model = WorkingPeriod
        exclude = ['task']


class PeriodCreateForm(PeriodEditForm):
    def __init__(self, *args, **kwargs):
        self.task = kwargs['initial'].pop('related_task')
        super(PeriodCreateForm, self).__init__(*args, **kwargs)
        self.fields['resource'].widget.q_filter = {'task__id': self.task.pk} #TODO: to the field and not the widget

    def clean_resource(self):
        resource = self.cleaned_data['resource']

        if resource not in self.task.get_resources():
            raise ValidationError(_(u"This resource has not been allocated to this task"))

        return resource

    def save(self):
        task = self.task
        self.instance.task = task

        if task.status_id == constants.NOT_STARTED_PK:
            task.status_id = constants.IN_PROGRESS_PK
            task.save()

        return super(PeriodCreateForm, self).save()
