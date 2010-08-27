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

from django.utils.translation import ugettext_lazy as _, ugettext
from django.forms import ValidationError

from creme_core.forms import CremeEntityForm
from creme_core.forms.fields import CremeEntityField

from persons.models import Contact

from projects.models import Resource


class ResourceEditForm(CremeEntityForm):
    linked_contact = CremeEntityField(label=_(u'Contact to be assigned to this task'),
                                      required=True, model=Contact)

    class Meta:
        model = Resource
        exclude = CremeEntityForm.Meta.exclude + ('task',)


class ResourceCreateForm(ResourceEditForm):
    def __init__(self, *args, **kwargs):
        self.related_task = kwargs['initial'].pop('related_task')
        super(ResourceCreateForm, self).__init__(*args, **kwargs)

    def clean_linked_contact(self):
        contact = self.cleaned_data['linked_contact']

        if self.related_task.resources_set.filter(linked_contact=contact):
            raise ValidationError(ugettext(u"This resource is already assigned to thsi task"))

        return contact

    def save(self):
        self.instance.task = self.related_task
        super(ResourceCreateForm, self).save()
