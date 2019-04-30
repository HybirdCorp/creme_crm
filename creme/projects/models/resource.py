# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from django.conf import settings
from django.db.models import ForeignKey, PositiveIntegerField, CASCADE
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from creme.creme_core.models import CremeEntity


# NB: no AbstractResource because resource should probably not be a CremeEntity at all...
# NB: CremeEntity and not CremeModel because we use a CreatorEntityField in WorkingPeriods' form
class Resource(CremeEntity):
    # TODO: set a editable (& use automatic formfield()) + not bulk_editable ?
    linked_contact = ForeignKey(settings.PERSONS_CONTACT_MODEL, on_delete=CASCADE,
                                verbose_name=_('Contact'), editable=False,
                               )
    hourly_cost    = PositiveIntegerField(_('Hourly cost'), default=0)
    task           = ForeignKey(settings.PROJECTS_TASK_MODEL, verbose_name=_('Task'),
                                related_name='resources_set',  # TODO: rename 'resources'
                                editable=False, on_delete=CASCADE,
                               )

    creation_label = _('Create a resource')
    save_label     = _('Save the resource')

    class Meta:
        app_label = 'projects'
        manager_inheritance_from_future = True
        verbose_name = _('Resource of project')
        verbose_name_plural = _('Resources of project')
        # TODO: unique_together (linked_contact, task)

    def __str__(self):
        return str(self.linked_contact)

    def get_absolute_url(self):
        return self.linked_contact.get_absolute_url()

    @staticmethod
    def get_clone_absolute_url():
        return ''

    def get_edit_absolute_url(self):
        return reverse('projects__edit_resource', args=(self.id,))

    def get_related_entity(self):
        return self.task

    def clone_for_task(self, task):
        new_resource = self.clone()
        new_resource.task = task
        new_resource.save()
