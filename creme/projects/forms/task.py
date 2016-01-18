# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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

from django.forms import DateTimeField, BooleanField, ValidationError
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.forms import CremeForm, CremeEntityForm
from creme.creme_core.forms.fields import CreatorEntityField, MultiCreatorEntityField
from creme.creme_core.forms.widgets import DateTimeWidget
from creme.creme_core.models import Relation
from creme.creme_core.utils import ellipsis_multi

from creme.activities.constants import REL_SUB_PART_2_ACTIVITY
from creme.activities.forms.activity_type import ActivityTypeField
from creme.activities.models import Activity, Calendar
from creme.activities.utils import check_activity_collisions

from .. import get_task_model
from ..constants import REL_SUB_LINKED_2_PTASK, REL_SUB_PART_AS_RESOURCE
from ..models import Resource


ProjectTask = get_task_model()


def _link_contact_n_activity(contact, activity, user):
    if contact.is_user:
        activity.calendars.add(Calendar.get_user_default_calendar(contact.is_user))

    create_rel = partial(Relation.objects.create,
                         subject_entity=contact,
                         object_entity=activity,
                         user=user,
                        )
    create_rel(type_id=REL_SUB_PART_2_ACTIVITY)
    create_rel(type_id=REL_SUB_PART_AS_RESOURCE)


class _TaskForm(CremeEntityForm):
    start = DateTimeField(label=_(u'Start'), widget=DateTimeWidget(), required=True)
    end   = DateTimeField(label=_(u'End'), widget=DateTimeWidget(), required=True)

    class Meta(CremeEntityForm.Meta):
        model = ProjectTask

    def __init__(self, *args, **kwargs):
        super(_TaskForm, self).__init__(*args, **kwargs)

        self.fields['duration'].required = True


class TaskEditForm(_TaskForm):
    pass  # TODO: replace _TaskForm with TaskEditForm


class TaskCreateForm(_TaskForm):
    parent_tasks = MultiCreatorEntityField(label=_(u'Parent tasks'), required=False, model=ProjectTask)

    def __init__(self, entity, *args, **kwargs):
        super(TaskCreateForm, self).__init__(*args, **kwargs)
        self._project = entity

        fields = self.fields
        fields['parent_tasks'].q_filter = {'project': entity.id}

    def save(self, *args, **kwargs):
        instance = self.instance
        project  = self._project

        instance.project = project
        instance.order   = project.attribute_order_task()

        super(TaskCreateForm, self).save(*args, **kwargs)

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


class RelatedActivityEditForm(CremeEntityForm):
    resource      = CreatorEntityField(label=_(u'Allocated resource'), model=Resource)
    start         = DateTimeField(label=_(u'Start'), widget=DateTimeWidget())  # TODO: required = False ??
    end           = DateTimeField(label=_(u'End'), widget=DateTimeWidget())
    type_selector = ActivityTypeField(label=_(u'Type'))

    class Meta(CremeEntityForm.Meta):
        model = Activity
        exclude = CremeEntityForm.Meta.exclude + ('title', 'is_all_day', 'minutes',
                                                  'status', 'type', 'sub_type',
                                                 )

    def __init__(self, *args, **kwargs):
        super(RelatedActivityEditForm, self).__init__(*args, **kwargs)
        fields = self.fields
        fields['duration'].required = True

        self.old_participant = self.old_relation = None
        instance = self.instance
        pk = instance.pk

        if pk:  # Edition
            fields['keep_participating'] = \
                BooleanField(label=_('If the contact changes, the old one '
                                     'keeps participating to the activities.'
                                    ),
                             required=False,
                            )

            get_relation = Relation.objects.get

            try:
                task = get_relation(subject_entity=pk, type=REL_SUB_LINKED_2_PTASK) \
                               .object_entity \
                               .get_real_entity()
                self.old_relation = get_relation(type=REL_SUB_PART_AS_RESOURCE,
                                                 object_entity=pk,
                                                )
            except Relation.DoesNotExist:
                raise ConflictError('This Activity is not related to a projet task')

            self.old_participant = self.old_relation.subject_entity.get_real_entity()
            fields['resource'].initial = Resource.objects.get(task=task,
                                                              linked_contact=self.old_participant,
                                                             )

            fields['type_selector'].initial = (instance.type_id, instance.sub_type_id)

    def clean(self, *args, **kwargs):
        cdata = self.cleaned_data

        if not self._errors:
            collisions = check_activity_collisions(cdata['start'], cdata['end'],
                                                   [cdata['resource'].linked_contact],
                                                   busy=cdata['busy'],
                                                   exclude_activity_id=self.instance.pk,
                                                  )

            if collisions:
                raise ValidationError(collisions)

        return cdata

    def save(self, *args, **kwargs):
        instance = self.instance
        cdata = self.cleaned_data
        instance.type, instance.sub_type = cdata['type_selector']

        super(RelatedActivityEditForm, self).save(*args, **kwargs)

        participant = cdata['resource'].linked_contact
        old_participant = self.old_participant

        if old_participant != participant:  # Creation mode OR edition mode with resource change
            if old_participant:
                self.old_relation.delete()

                if not cdata.get('keep_participating'):
                    # NB: no delete() on queryset (with a filter()) in order to send signals
                    Relation.objects.get(subject_entity=old_participant.id,
                                         type=REL_SUB_PART_2_ACTIVITY,
                                         object_entity=instance.pk,
                                        ).delete()

            _link_contact_n_activity(participant, instance, self.user)

        return instance


class RelatedActivityCreateForm(RelatedActivityEditForm):
    def __init__(self, *args, **kwargs):
        super(RelatedActivityCreateForm, self).__init__(*args, **kwargs)
        self._task = self.initial['task']

    def save(self, *args, **kwargs):
        instance = self.instance
        task = self._task
        p_name, t_name = ellipsis_multi((task.project.name, task.title),
                                        # 9 is the length of ' -  - XYZ' (ie: the 'empty' format string)
                                        Activity._meta.get_field('title').max_length - 9
                                       )
        instance.title = u'%s - %s - %003d' % (p_name, t_name, len(task.related_activities) + 1)

        super(RelatedActivityCreateForm, self).save(*args, **kwargs)

        Relation.objects.create(subject_entity=instance,
                                type_id=REL_SUB_LINKED_2_PTASK,
                                object_entity=task,
                                user=self.user,
                               )

        return instance
