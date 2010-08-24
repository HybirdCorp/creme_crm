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



from django.forms.models import ModelChoiceField, IntegerField
from django.forms import TimeField

from activities.models import ActivityType, Task, TaskStatus
from activities.constants import ACTIVITYTYPE_TASK
from django.forms.widgets import HiddenInput
from activity import ActivityCreateForm, ActivityEditForm, ActivityCreateWithoutRelationForm

from creme_core.forms.widgets import CalendarWidget, TimeWidget, RelationListWidget


class TaskCreateForm(ActivityCreateForm):
    class Meta:
        model = Task
        exclude = ActivityCreateForm.Meta.exclude

    end_time = TimeField(widget=HiddenInput(),required=False)
    type = ModelChoiceField(empty_label=None, queryset=ActivityType.objects.filter(pk=ACTIVITYTYPE_TASK))

    def __init__(self, *args, **kwargs):
        super(TaskCreateForm, self).__init__(*args, **kwargs)
        self.fields['type'].initial = ActivityType.objects.get(pk=ACTIVITYTYPE_TASK)
        self.fields['my_participation'].label = 'Est ce que je participe à cette tâche'
        
    def save(self):
        self.cleaned_data['type'] = ActivityType.objects.get(pk=ACTIVITYTYPE_TASK)
        super(TaskCreateForm, self).save()

class TaskCreateWithoutRelationForm(ActivityCreateWithoutRelationForm):
    class Meta:
        model = Task
        exclude = ActivityCreateWithoutRelationForm.Meta.exclude

    type = ModelChoiceField(empty_label=None, queryset=ActivityType.objects.filter(pk=ACTIVITYTYPE_TASK))

    def __init__(self, *args, **kwargs):
        super(TaskCreateWithoutRelationForm, self).__init__(*args, **kwargs)
        self.fields['type'].initial = ActivityType.objects.get(pk=ACTIVITYTYPE_TASK)
        self.fields['my_participation'].label = 'Est ce que je participe à cette tâche'

    def save(self):
        self.cleaned_data['type'] = ActivityType.objects.get(pk=ACTIVITYTYPE_TASK)
        super(MeetingCreateWithoutRelationForm, self).save()
        

class TaskEditForm(ActivityEditForm):
    class Meta:
        model = Task
        exclude = ActivityEditForm.Meta.exclude
