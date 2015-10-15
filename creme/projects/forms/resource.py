# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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

from django.forms.fields import BooleanField
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.forms import CremeEntityForm
from creme.creme_core.forms.fields import CreatorEntityField
from creme.creme_core.models import Relation

from creme.persons import get_contact_model
#from creme.persons.models import Contact

from creme.activities.constants import REL_SUB_PART_2_ACTIVITY

from ..constants import REL_SUB_PART_AS_RESOURCE
from ..models import Resource
from .task import _link_contact_n_activity


class ResourceCreateForm(CremeEntityForm):
    contact = CreatorEntityField(label=_(u'Contact to be assigned to this task'),
                                 model=get_contact_model(),
                                )

    class Meta(CremeEntityForm.Meta):
        model = Resource

    def __init__(self, task, *args, **kwargs):
        super(ResourceCreateForm, self).__init__(*args, **kwargs)
        instance = self.instance
        instance.task = task

        other_resources = task.resources_set.all()

        if instance.pk:
            other_resources = other_resources.exclude(pk=instance.pk)

        contact_f = self.fields['contact']
        contact_f.q_filter = {
                '~pk__in': list(other_resources.values_list('linked_contact_id', flat=True)),
            }
#        # hack : The 'q_filter' disable creation when 'creation_action_url' is empty because default creation views
#        # cannot return filtered instances.
#        # So this weird line forces a value in 'creation_action_url' in order re-enable creation button.
        # The creation view cannot create a Contact already related to Resource (& so, excluded).
#        contact_f.create_action_url = contact_f.create_action_url
        contact_f.force_creation = True # TODO: in constructor

    def save(self, *args, **kwargs):
        self.instance.linked_contact = self.cleaned_data['contact']
        return super(ResourceCreateForm, self).save(*args, **kwargs)


class ResourceEditForm(ResourceCreateForm):
    keep_participating = BooleanField(label=_('If the contact changes, the old one '
                                              'keeps participating to the activities.'
                                             ),
                                      required=False,
                                     )

    def __init__(self, *args, **kwargs):
        super(ResourceEditForm, self).__init__(*args, **kwargs)
        self.old_contact = self.instance.linked_contact

    def save(self, *args, **kwargs):
        old_contact = self.old_contact
        new_contact = self.cleaned_data['contact']

        if old_contact != new_contact:
            task_activities = self.instance.task.related_activities
            activities_ids = {activity.id
                                for activity in task_activities
                                    if activity.projects_resource.linked_contact == old_contact
                             }

            atypes = [REL_SUB_PART_AS_RESOURCE]
            if not self.cleaned_data.get('keep_participating'):
                atypes.append(REL_SUB_PART_2_ACTIVITY)

            for r in Relation.objects.filter(subject_entity=old_contact, type__in=atypes,
                                             object_entity__in=[a.id for a in task_activities],
                                            ): # NB: no delete() on queryset in order to send signals
                r.delete()

            for activity in task_activities:
                if activity.id in activities_ids:
                    _link_contact_n_activity(new_contact, activity, self.user)

        return super(ResourceEditForm, self).save(*args, **kwargs)
