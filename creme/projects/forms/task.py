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

from django.contrib.auth.models import User
from django.forms import DateTimeField, ValidationError
from django.forms.models import ModelMultipleChoiceField
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.forms import CremeForm, CremeEntityForm
from creme.creme_core.forms.fields import MultiCremeEntityField
from creme.creme_core.forms.validators import validate_linkable_entities
from creme.creme_core.forms.widgets import DateTimeWidget, UnorderedMultipleChoiceWidget
from creme.creme_core.models.relation import Relation

from creme.persons.models.contact import Contact

from creme.activities.constants import REL_SUB_PART_2_ACTIVITY, REL_OBJ_PART_2_ACTIVITY
from creme.activities.models.activity import Calendar
from creme.activities.utils import check_activity_collisions

from ..models import ProjectTask


class _TaskForm(CremeEntityForm):
    start = DateTimeField(label=_(u'Start'), widget=DateTimeWidget(), required=True)
    end   = DateTimeField(label=_(u'End'), widget=DateTimeWidget(), required=True)

    class Meta(CremeEntityForm.Meta):
        model = ProjectTask
        exclude = CremeEntityForm.Meta.exclude + ('is_all_day', 'calendars', 'type', 'project', 'order', 'status', 'parent_tasks')

    def __init__(self, *args, **kwargs):
        super(_TaskForm, self).__init__(*args, **kwargs)
        self.participants = []

    def clean(self, *args, **kwargs):
        cleaned_data = self.cleaned_data

        if not self._errors:
            collisions = check_activity_collisions(cleaned_data['start'], cleaned_data['end'], self.participants, busy=cleaned_data['busy'], exclude_activity_id=self.instance.pk)
            if collisions:
                raise ValidationError(collisions)

        return cleaned_data


class TaskEditForm(_TaskForm):
    def __init__(self, *args, **kwargs):
        super(TaskEditForm, self).__init__(*args, **kwargs)
        self.participants = self.instance.get_related_entities(REL_OBJ_PART_2_ACTIVITY)


class TaskCreateForm(_TaskForm):
    parent_tasks = MultiCremeEntityField(label=_(u'Parent tasks'), required=False, model=ProjectTask)
    participating_users = ModelMultipleChoiceField(label=_(u'Calendars'), queryset=User.objects.all(),
                                                   required=False, widget=UnorderedMultipleChoiceWidget)

    def __init__(self, entity, *args, **kwargs):
        super(TaskCreateForm, self).__init__(*args, **kwargs)

        self._project = entity

        fields = self.fields
        fields['participating_users'].widget.attrs = {'reduced':'true'}
        fields['parent_tasks'].q_filter = {'project': entity.id}

    def clean_participating_users(self):
        users = self.cleaned_data['participating_users']
        self.participants.extend(validate_linkable_entities(Contact.objects.filter(is_user__in=users), self.user))
        return users

    def save(self, *args, **kwargs):
        instance = self.instance
        project  = self._project

        instance.project = project
        instance.order   = project.attribute_order_task()

        super(TaskCreateForm, self).save(*args, **kwargs)

        for part_user in self.participants:
            Relation.objects.create(subject_entity=part_user, type_id=REL_SUB_PART_2_ACTIVITY, object_entity=instance, user=instance.user)
            instance.calendars.add(Calendar.get_user_default_calendar(part_user.is_user))


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
        tasks = self.task.parent_tasks

        for parent in self.cleaned_data['parents']:
            tasks.add(parent)
