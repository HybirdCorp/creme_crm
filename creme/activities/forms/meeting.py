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

from django.forms.models import ModelChoiceField

from activities.models import ActivityType, Meeting
from activities.constants import ACTIVITYTYPE_MEETING
from activity import ActivityCreateForm, ActivityEditForm, ActivityCreateWithoutRelationForm


class MeetingCreateForm(ActivityCreateForm):
    class Meta:
        model = Meeting
        exclude = ActivityCreateForm.Meta.exclude

    type = ModelChoiceField(empty_label=None, queryset=ActivityType.objects.filter(pk=ACTIVITYTYPE_MEETING)) #TODO: exclude....

    def __init__(self, *args, **kwargs):
        super(MeetingCreateForm, self).__init__(*args, **kwargs)
        self.fields['type'].initial = ActivityType.objects.get(pk=ACTIVITYTYPE_MEETING)

    def save(self):
        self.cleaned_data['type'] = ActivityType.objects.get(pk=ACTIVITYTYPE_MEETING)
        super(MeetingCreateForm, self).save()


class MeetingCreateWithoutRelationForm(ActivityCreateWithoutRelationForm):
    class Meta:
        model = Meeting
        exclude = ActivityCreateWithoutRelationForm.Meta.exclude

    type = ModelChoiceField(empty_label=None, queryset=ActivityType.objects.filter(pk=ACTIVITYTYPE_MEETING))

    def __init__(self, *args, **kwargs):
        super(MeetingCreateWithoutRelationForm, self).__init__(*args, **kwargs)
        self.fields['type'].initial = ActivityType.objects.get(pk=ACTIVITYTYPE_MEETING)

    def save(self):
        self.cleaned_data['type'] = ActivityType.objects.get(pk=ACTIVITYTYPE_MEETING) #TODO: self.instance.type_id = ACTIVITYTYPE_MEETING instead
        super(MeetingCreateWithoutRelationForm, self).save()


class MeetingEditForm(ActivityEditForm):
    class Meta:
        model = Meeting
        exclude = ActivityEditForm.Meta.exclude
