# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

# import warnings
from functools import partial

from django.db.models.query_utils import Q
from django.forms import BooleanField, ValidationError
from django.utils.translation import gettext_lazy as _

from creme.activities.constants import REL_SUB_PART_2_ACTIVITY
from creme.activities.forms.activity_type import ActivityTypeField
from creme.activities.models import Activity, Calendar
from creme.activities.utils import check_activity_collisions
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.forms import (
    CreatorEntityField,
    CremeEntityForm,
    CremeForm,
    MultiCreatorEntityField,
)
from creme.creme_core.gui.custom_form import CustomFormExtraSubCell
from creme.creme_core.models import Relation
from creme.creme_core.utils import ellipsis_multi
from creme.persons import get_contact_model

from .. import get_task_model
from ..constants import REL_SUB_LINKED_2_PTASK, REL_SUB_PART_AS_RESOURCE

# Contact = get_contact_model()
ProjectTask = get_task_model()


def _link_contact_n_activity(contact, activity, user):
    if contact.is_user:
        activity.calendars.add(Calendar.objects.get_default_calendar(contact.is_user))

    create_rel = partial(
        Relation.objects.safe_create,
        subject_entity=contact,
        object_entity=activity,
        user=user,
    )
    create_rel(type_id=REL_SUB_PART_2_ACTIVITY)
    create_rel(type_id=REL_SUB_PART_AS_RESOURCE)


class ParentTasksSubCell(CustomFormExtraSubCell):
    sub_type_id = 'projects_parent_tasks'
    verbose_name = _('Parent tasks')

    def formfield(self, instance, user, **kwargs):
        return MultiCreatorEntityField(
            label=self.verbose_name,
            required=False,
            model=ProjectTask,
            user=user,
            # NB: not <linked_project.id> because <linked_project> can be None
            #     in creme_config brick.
            q_filter={'linked_project': instance.linked_project_id},
        )


class BaseTaskCreationCustomForm(CremeEntityForm):
    # NB: entity=None because the form could be instantiated by creme_config
    def __init__(self, entity=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.linked_project = entity

    def save(self, *args, **kwargs):
        # instance = self.instance
        # instance.order = instance.linked_project.attribute_order_task()
        #
        # super().save(*args, **kwargs)
        instance = super().save(*args, **kwargs)

        add_parent = instance.parent_tasks.add
        for parent in self.cleaned_data[self.subcell_key(ParentTasksSubCell)]:
            add_parent(parent)

        return instance


# class _TaskForm(CremeEntityForm):
#     class Meta(CremeEntityForm.Meta):
#         model = ProjectTask
#
#     def __init__(self, *args, **kwargs):
#         warnings.warn('projects.forms.task._TaskForm is deprecated.', DeprecationWarning)
#         super().__init__(*args, **kwargs)


# class TaskEditForm(_TaskForm):
#     def __init__(self, entity, *args, **kwargs):
#         warnings.warn('TaskEditForm is deprecated.', DeprecationWarning)
#         super().__init__(*args, **kwargs)


# class TaskCreateForm(_TaskForm):
#     parent_tasks = MultiCreatorEntityField(
#         label=_('Parent tasks'), required=False, model=ProjectTask,
#     )
#
#     def __init__(self, entity, *args, **kwargs):
#         warnings.warn('TaskCreateForm is deprecated.', DeprecationWarning)
#         super().__init__(*args, **kwargs)
#         self._project = entity
#
#         fields = self.fields
#         fields['parent_tasks'].q_filter = {'linked_project': entity.id}
#
#     def save(self, *args, **kwargs):
#         instance = self.instance
#         project = self._project
#
#         instance.linked_project = project
#         instance.order = project.attribute_order_task()
#
#         super().save(*args, **kwargs)
#
#         return instance


class TaskAddParentForm(CremeForm):
    parents = MultiCreatorEntityField(label=_('Parent tasks'), required=False, model=ProjectTask)

    class Meta:
        model = ProjectTask

    def __init__(self, instance, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task = instance
        self.fields['parents'].q_filter = (
            Q(linked_project=instance.linked_project_id)
            & ~Q(id__in=[t.id for t in instance.get_subtasks()])
            # & ~Q(children_set=instance.pk)
            & ~Q(children=instance.pk)
        )

    def save(self, *args, **kwargs):
        add_parent = self.task.parent_tasks.add

        for parent in self.cleaned_data['parents']:
            add_parent(parent)


class RelatedActivityEditForm(CremeEntityForm):
    # resource = CreatorEntityField(label=_('Allocated resource'), model=Contact)
    resource = CreatorEntityField(label=_('Allocated resource'), model=get_contact_model())
    type_selector = ActivityTypeField(label=_('Type'))

    class Meta(CremeEntityForm.Meta):
        model = Activity
        exclude = (
            *CremeEntityForm.Meta.exclude,
            'title', 'is_all_day', 'minutes', 'status', 'type', 'sub_type',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fields = self.fields
        fields['duration'].required = True
        fields['start'].required = True
        fields['end'].required = True

        self.old_participant = self.old_relation = None
        instance = self.instance
        pk = instance.pk

        task = self._get_task()

        resource_f = fields['resource']
        resource_f.q_filter = {'resource__task_id': task.id}

        if pk:  # Edition
            fields['keep_participating'] = BooleanField(
                label=_(
                    'If the contact changes, the old one keeps participating to the activities.'
                ),
                required=False,
            )

            get_relation = Relation.objects.get

            try:
                self.old_relation = get_relation(
                    type=REL_SUB_PART_AS_RESOURCE, object_entity=pk,
                )
            except Relation.DoesNotExist as e:
                raise ConflictError('This Activity is not related to a project task') from e

            self.old_participant = self.old_relation.subject_entity.get_real_entity()
            resource_f.initial = self.old_participant

            fields['type_selector'].initial = (instance.type_id, instance.sub_type_id)

    def _get_task(self):
        try:
            return Relation.objects.get(
                subject_entity=self.instance.pk, type=REL_SUB_LINKED_2_PTASK,
            ).object_entity.get_real_entity()
        except Relation.DoesNotExist as e:
            raise ConflictError('This Activity is not related to a project task.') from e

    def clean(self, *args, **kwargs):
        cdata = self.cleaned_data

        if not self._errors:
            collisions = check_activity_collisions(
                cdata['start'], cdata['end'],
                [cdata['resource']],
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

        super().save(*args, **kwargs)

        participant = cdata['resource']
        old_participant = self.old_participant

        if old_participant != participant:  # Creation mode OR edition mode with resource change
            if old_participant:
                self.old_relation.delete()

                if not cdata.get('keep_participating'):
                    # NB: no delete() on queryset (with a filter()) in order to send signals
                    Relation.objects.get(
                        subject_entity=old_participant.id,
                        type=REL_SUB_PART_2_ACTIVITY,
                        object_entity=instance.pk,
                    ).delete()

            _link_contact_n_activity(participant, instance, self.user)

        return instance


class RelatedActivityCreateForm(RelatedActivityEditForm):
    def __init__(self, entity, *args, **kwargs):
        self._task = entity
        super().__init__(*args, **kwargs)

    def _get_relations_to_create(self):
        instance = self.instance

        return super()._get_relations_to_create().append(Relation(
            subject_entity=instance,
            type_id=REL_SUB_LINKED_2_PTASK,
            object_entity=self._task,
            user=instance.user,
        ))

    def _get_task(self):
        return self._task

    def save(self, *args, **kwargs):
        task = self._task
        p_name, t_name = ellipsis_multi(
            (task.linked_project.name, task.title),
            # 9 is the length of ' -  - XYZ' (ie: the 'empty' format string)
            Activity._meta.get_field('title').max_length - 9
        )
        self.instance.title = '{project} - {task} - {count:03}'.format(
            project=p_name,
            task=t_name,
            count=len(task.related_activities) + 1,
        )

        return super().save(*args, **kwargs)
