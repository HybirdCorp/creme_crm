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
from django.utils.translation import ugettext_lazy as _
from django.forms import ValidationError
from django.forms.widgets import HiddenInput

from creme_core.forms.fields import CremeEntityField
from creme_core.forms.fields import MultiCremeEntityField
from creme_core.forms import CremeEntityForm
from creme_core.forms.widgets import DateTimeWidget

from projects.models import ProjectTask, Project


class TaskEditForm(CremeEntityForm):
    start        = DateTimeField(label=_(u'Début'), widget=DateTimeWidget(), required = True)
    end          = DateTimeField(label=_(u'Fin'), widget=DateTimeWidget(), required = True)
    parents_task = MultiCremeEntityField(label=_(u'Tâche(s) parente(s)'),
                                         required=False, model=ProjectTask)

    def clean_parents_task(self):
        parents = self.cleaned_data['parents_task']

        for parent in parents:
            if parent == self.instance:
                raise ValidationError(_(u"Une tâche ne peut pas être parente d'elle même"))

        return parents

    class Meta:
        model = ProjectTask
        exclude = CremeEntityForm.Meta.exclude + ('is_all_day', 'type', 'project', 'order')


class TaskCreateForm(TaskEditForm):
    project = CremeEntityField(model=Project, required=True, widget=HiddenInput())

    class Meta:
        model = ProjectTask
        exclude = CremeEntityForm.Meta.exclude + ('is_all_day', 'type', 'order')

    def save(self):
        task = super(TaskCreateForm, self).save()
        task.order = task.project.attribute_order_task()
        task.save()
