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

from functools import partial

from django.contrib.auth.models import User
from django.forms import DateTimeField, ValidationError, ModelMultipleChoiceField, ModelChoiceField
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.forms import CremeForm, CremeEntityForm #FieldBlockManager
from creme.creme_core.forms.fields import MultiCreatorEntityField
from creme.creme_core.forms.validators import validate_linkable_entities
from creme.creme_core.forms.widgets import DateTimeWidget, UnorderedMultipleChoiceWidget
from creme.creme_core.models import Relation

#from creme.creme_config.forms.fields import CreatorModelChoiceField

from creme.persons.models import Contact

from creme.activities.constants import REL_SUB_PART_2_ACTIVITY, REL_OBJ_PART_2_ACTIVITY
from creme.activities.forms.activity_type import ActivityTypeField
from creme.activities.models import Calendar, ActivitySubType
from creme.activities.utils import check_activity_collisions

from ..models import ProjectTask


#TODO use clean interval to match business rules of activities form ??
class _TaskForm(CremeEntityForm):
    start = DateTimeField(label=_(u'Start'), widget=DateTimeWidget(), required=True)
    end   = DateTimeField(label=_(u'End'), widget=DateTimeWidget(), required=True)

    class Meta(CremeEntityForm.Meta):
        model = ProjectTask
        #exclude = CremeEntityForm.Meta.exclude + ('is_all_day', 'calendars', 'type', 'project', 'order', 'status', 'parent_tasks')
        exclude = CremeEntityForm.Meta.exclude + ('is_all_day', 'minutes', 'status')

    def __init__(self, *args, **kwargs):
        super(_TaskForm, self).__init__(*args, **kwargs)
        self.participants = []

    def clean(self, *args, **kwargs):
        cleaned_data = self.cleaned_data

        if not self._errors:
            collisions = check_activity_collisions(cleaned_data['start'], cleaned_data['end'],
                                                   self.participants, busy=cleaned_data['busy'],
                                                   exclude_activity_id=self.instance.pk,
                                                  )
            if collisions:
                raise ValidationError(collisions)

        return cleaned_data


class TaskEditForm(_TaskForm):
    sub_type = ModelChoiceField(label=_('Activity type'), queryset=ActivitySubType.objects.none(), required=False)
    #sub_type = CreatorModelChoiceField(label=_('Activity type'), required=False, 
                                        #queryset=ActivitySubType.objects.none(),
                                        #) TODO

    #blocks = FieldBlockManager(('general', _(u'General information'), ['user', 'title', 'duration', 'sub_type', 'start',
                                                                        #'end', 'busy', 'tstatus', 'description', 'place']),
                                #)

    #class Meta(_TaskForm.Meta):
        #exclude = _TaskForm.Meta.exclude + ('is_all_day', 'type', 'calendars', 'project', 'order', 'status', 'parent_tasks', 'floating_type')

    def __init__(self, *args, **kwargs):
        super(TaskEditForm, self).__init__(*args, **kwargs)

        instance = self.instance
        self.fields['sub_type'].queryset = ActivitySubType.objects.filter(type=instance.type)
        self.participants = instance.get_related_entities(REL_OBJ_PART_2_ACTIVITY)


class TaskCreateForm(_TaskForm):
    type_selector = ActivityTypeField(label=_(u"Task's nomenclature"))
    parent_tasks = MultiCreatorEntityField(label=_(u'Parent tasks'), required=False, model=ProjectTask)
    participating_users = ModelMultipleChoiceField(label=_(u'Participating users'),
                                                   queryset=User.objects.filter(is_staff=False),
                                                   required=False,
                                                   widget=UnorderedMultipleChoiceWidget,
                                                  )

    #blocks = FieldBlockManager(('general', _(u'General information'), ['user', 'title', 'duration', 'type_selector', 'start',
                                                                        #'end', 'busy', 'tstatus', 'description', 'place',
                                                                        #'parent_tasks', 'participating_users']),
                                #)

    class Meta(_TaskForm.Meta):
        #exclude = _TaskForm.Meta.exclude + ('project', 'order', 'type', 'calendars', 'is_all_day',
                                            #'parent_tasks', 'floating_type', 'minutes', 'status', 'sub_type',
                                            #)
        exclude = _TaskForm.Meta.exclude + ('sub_type',)

    def __init__(self, entity, *args, **kwargs):
        super(TaskCreateForm, self).__init__(*args, **kwargs)

        self._project = entity

        fields = self.fields
        fields['participating_users'].widget.attrs = {'reduced': 'true'}
        fields['parent_tasks'].q_filter = {'project': entity.id}

    def clean_participating_users(self):
        users = self.cleaned_data['participating_users']
        self.participants.extend(
                validate_linkable_entities(
                        Contact.objects.filter(is_user__in=users), self.user
                    )
            )
        return users

    def save(self, *args, **kwargs):
        instance = self.instance
        project  = self._project

        instance.project = project
        instance.order   = project.attribute_order_task()
        instance.type, instance.sub_type = self.cleaned_data['type_selector']

        super(TaskCreateForm, self).save(*args, **kwargs)

        create_rel = partial(Relation.objects.create, type_id=REL_SUB_PART_2_ACTIVITY,
                             object_entity=instance, user=instance.user,
                            )
        add_calendar = instance.calendars.add

        for part_user in self.participants:
            create_rel(subject_entity=part_user)
            add_calendar(Calendar.get_user_default_calendar(part_user.is_user))

        return instance


class TaskAddParentForm(CremeForm):
    parents = MultiCreatorEntityField(label=_(u'Parent tasks'), required=False, model=ProjectTask)

    class Meta:
        model = ProjectTask

    def __init__(self, instance, *args, **kwargs):
        super(TaskAddParentForm, self).__init__(*args, **kwargs)
        self.task = instance
        self.fields['parents'].q_filter = {'project':       instance.project_id,
                                           '~id__in':       [t.id for t in instance.get_subtasks()],
                                           '~children_set': instance.pk,
                                          }

    def save(self, *args, **kwargs):
        add_parent = self.task.parent_tasks.add

        for parent in self.cleaned_data['parents']:
            add_parent(parent)
