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

from django.db.models.query_utils import Q
from django.forms.fields import BooleanField
from django.utils.translation import gettext_lazy as _

from creme.activities.constants import REL_SUB_PART_2_ACTIVITY
from creme.creme_core.forms import CreatorEntityField, CremeModelForm
from creme.creme_core.models import Relation
from creme.persons import get_contact_model

from ..constants import REL_SUB_PART_AS_RESOURCE
from ..models import Resource
from .task import _link_contact_n_activity


# Not CremeEntityForm to avoid Relations/CremeProperties fields
class ResourceCreateForm(CremeModelForm):
    contact = CreatorEntityField(
        label=_('Contact to be assigned to this task'),
        model=get_contact_model(),
    )

    class Meta(CremeModelForm.Meta):
        model = Resource

    def __init__(self, task, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance
        instance.task = task

        other_resources = task.resources_set.all()

        if instance.pk:
            other_resources = other_resources.exclude(pk=instance.pk)

        contact_f = self.fields['contact']
        contact_f.q_filter = ~Q(
            pk__in=[*other_resources.values_list('linked_contact_id', flat=True)],
        )

        # The creation view cannot create a Contact already related to Resource (& so, excluded).
        contact_f.force_creation = True  # TODO: in constructor ?

    def save(self, *args, **kwargs):
        self.instance.linked_contact = self.cleaned_data['contact']
        return super().save(*args, **kwargs)


class ResourceEditForm(ResourceCreateForm):
    keep_participating = BooleanField(
        label=_(
            'If the contact changes, the old one '
            'keeps participating to the activities.'
        ),
        required=False,
    )

    def __init__(self, entity, *args, **kwargs):
        super().__init__(task=entity, *args, **kwargs)
        self.old_contact = self.fields['contact'].initial = self.instance.linked_contact

    def save(self, *args, **kwargs):
        old_contact = self.old_contact
        new_contact = self.cleaned_data['contact']

        if old_contact != new_contact:
            task_activities = self.instance.task.related_activities
            activities_ids = {
                activity.id
                for activity in task_activities
                if activity.projects_resource.linked_contact == old_contact
            }

            atypes = [REL_SUB_PART_AS_RESOURCE]
            if not self.cleaned_data.get('keep_participating'):
                atypes.append(REL_SUB_PART_2_ACTIVITY)

            for r in Relation.objects.filter(
                subject_entity=old_contact,
                type__in=atypes,
                object_entity__in=[a.id for a in task_activities],
            ):
                # NB: no delete() on queryset in order to send signals
                r.delete()

            for activity in task_activities:
                if activity.id in activities_ids:
                    _link_contact_n_activity(new_contact, activity, self.user)

        return super().save(*args, **kwargs)
