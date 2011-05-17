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

from django.forms import DateTimeField, ValidationError
from django.utils.translation import ugettext_lazy as _, ugettext
from django.forms.widgets import HiddenInput

from creme_core.forms import CremeEntityForm
from creme_core.forms.fields import MultiCremeEntityField
from creme_core.forms.widgets import DateTimeWidget

from projects.models import ProjectTask


class TaskEditForm(CremeEntityForm):
    start        = DateTimeField(label=_(u'Start'), widget=DateTimeWidget(), required=True)
    end          = DateTimeField(label=_(u'End'), widget=DateTimeWidget(), required=True)
    parents_task = MultiCremeEntityField(label=_(u'Parent tasks'), required=False, model=ProjectTask)

    def __init__(self, *args, **kwargs):
        super(TaskEditForm, self).__init__(*args, **kwargs)
        self._project_id = self.instance.project_id
        self._set_parent_task_q()

    class Meta:
        model = ProjectTask
        exclude = CremeEntityForm.Meta.exclude + ('is_all_day', 'type', 'project', 'order', 'status')

    def clean_parents_task(self):
        parents  = self.cleaned_data['parents_task']
        instance = self.instance

        project_id = self._project_id
        children_ids = []
        if instance.pk is not None:
            children_ids = instance.get_children_ids()

        #TODO: use a q_filter to avoid selecting itself; check true cycle
        for parent in parents:
            if parent == instance:
                raise ValidationError(ugettext(u"A task can't be its own parent"))

            if parent.project_id != project_id:
                raise ValidationError(ugettext(u"Parent tasks have to be in the same project. «%s» doesn't belong to the same project.") % parent)

            if parent.id in children_ids:
                raise ValidationError(ugettext(u"«%s» is an indirect child of this task.") % parent)

        return parents

    def _set_parent_task_q(self):
        pk = self.instance.pk
        children_ids = [pk]
        
        if pk is not None:
            children_ids.extend(self.instance.get_children_ids())

        #NB: Don't exclude current parent tasks, because if the user 'unselected' it without saving,
        #    he couldn't select it again without closing & re-opening the form
        self.fields['parents_task'].q_filter = {'project':self._project_id, '~id__in': children_ids, '~parents_task__id':pk}

        
class TaskCreateForm(TaskEditForm):
    def __init__(self, entity, *args, **kwargs):
        super(TaskCreateForm, self).__init__(*args, **kwargs)
        self._project    = entity
        self._project_id = entity.id
        self._set_parent_task_q()

    def save(self, *args, **kwargs):
        instance = self.instance
        project  = self._project

        instance.project = project
        instance.order   = project.attribute_order_task()

        return super(TaskCreateForm, self).save(*args, **kwargs)
