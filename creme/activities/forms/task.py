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

from django.utils.translation import ugettext as _
from django.forms import TimeField
from django.forms.widgets import HiddenInput

from activities.models import Task
from activity import ActivityCreateForm, RelatedActivityCreateForm


class RelatedTaskCreateForm(RelatedActivityCreateForm):
    end_time = TimeField(widget=HiddenInput(), required=False)

    class Meta(RelatedActivityCreateForm.Meta):
        model = Task
        exclude = RelatedActivityCreateForm.Meta.exclude + ('type',)

    def __init__(self, *args, **kwargs):
        super(RelatedTaskCreateForm, self).__init__(*args, **kwargs)
        self.fields['my_participation'].label = _(u'Do I participate to this task')


class TaskCreateWithoutRelationForm(ActivityCreateForm):
    class Meta(ActivityCreateForm.Meta):
        model = Task
        exclude = ActivityCreateForm.Meta.exclude + ('type',)

    def __init__(self, *args, **kwargs):
        super(TaskCreateWithoutRelationForm, self).__init__(*args, **kwargs)
        self.fields['my_participation'].label = _(u'Do I participate to this task')
