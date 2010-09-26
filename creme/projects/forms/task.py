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

from django.forms import DateTimeField
from django.utils.translation import ugettext_lazy as _, ugettext
from django.forms import ValidationError
from django.forms.widgets import HiddenInput

from creme_core.forms import CremeEntityForm
from creme_core.forms.fields import MultiCremeEntityField
from creme_core.forms.widgets import DateTimeWidget

from projects.models import ProjectTask


class TaskEditForm(CremeEntityForm):
    start        = DateTimeField(label=_(u'Start'), widget=DateTimeWidget(), required=True)
    end          = DateTimeField(label=_(u'End'), widget=DateTimeWidget(), required=True)
    parents_task = MultiCremeEntityField(label=_(u'Parent tasks'), required=False, model=ProjectTask)

    class Meta:
        model = ProjectTask
        exclude = CremeEntityForm.Meta.exclude + ('is_all_day', 'type', 'project', 'order')

    def clean_parents_task(self):
        parents  = self.cleaned_data['parents_task']
        instance = self.instance

        for parent in parents:
            if parent == instance:
                raise ValidationError(ugettext(u"A task can't be its own parent"))

        return parents


class TaskCreateForm(TaskEditForm):
    class Meta:
        model = ProjectTask
        exclude = CremeEntityForm.Meta.exclude + ('is_all_day', 'type', 'order', 'project')

    def __init__(self, project, *args, **kwargs):
        super(TaskCreateForm, self).__init__(*args, **kwargs)
        self._project = project

    #TODO: don't save twice ??
    def save(self):
        instance = self.instance
        instance.project = self._project
        super(TaskCreateForm, self).save()

        instance.order = instance.project.attribute_order_task()
        instance.save()

        return instance
