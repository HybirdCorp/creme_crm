# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from django.forms import DateTimeField, ValidationError
from django.utils.translation import ugettext_lazy as _, ugettext
from django.forms.widgets import HiddenInput

from creme_core.forms import CremeForm, CremeEntityForm
from creme_core.forms.fields import MultiCremeEntityField
from creme_core.forms.widgets import DateTimeWidget

from projects.models import ProjectTask


class TaskEditForm(CremeEntityForm):
    start = DateTimeField(label=_(u'Start'), widget=DateTimeWidget(), required=True)
    end   = DateTimeField(label=_(u'End'), widget=DateTimeWidget(), required=True)

    class Meta:
        model = ProjectTask
        exclude = CremeEntityForm.Meta.exclude + ('is_all_day', 'type', 'project', 'order', 'status', 'parents_task')


class TaskCreateForm(TaskEditForm):
    parents_task = MultiCremeEntityField(label=_(u'Parent tasks'), required=False, model=ProjectTask)

    def __init__(self, entity, *args, **kwargs):
        super(TaskCreateForm, self).__init__(*args, **kwargs)
        self._project = entity

        self.fields['parents_task'].q_filter = {'project': entity.id}

    def save(self, *args, **kwargs):
        instance = self.instance
        project  = self._project

        instance.project = project
        instance.order   = project.attribute_order_task()

        return super(TaskCreateForm, self).save(*args, **kwargs)


class TaskAddParentForm(CremeForm):
    parents = MultiCremeEntityField(label=_(u'Parent tasks'), required=False, model=ProjectTask)

    class Meta:
        model = ProjectTask

    def __init__(self, instance, *args, **kwargs):
        super(TaskAddParentForm, self).__init__(*args, **kwargs)
        self.task = instance
        self.fields['parents'].q_filter = {
                'project':       instance.project_id,
                '~id__in':       [t.id for t in instance.get_subtasks()],
                '~children_set': instance.pk,
            }

    def save(self, *args, **kwargs):
        tasks = self.task.parents_task

        for parent in self.cleaned_data['parents']:
            tasks.add(parent)
