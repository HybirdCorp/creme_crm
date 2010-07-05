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

from datetime import datetime, time

from django.forms.fields import DateTimeField, TimeField
from django.utils.translation import ugettext_lazy as _

from creme_core.forms import CremeModelWithUserForm
from creme_core.forms.widgets import CalendarWidget, TimeWidget

from assistants.models import Action


class ActionEditForm(CremeModelWithUserForm):
    deadline      = DateTimeField(label=_(u"Date d'échéance"), widget=CalendarWidget())
    deadline_time = TimeField(label=_(u'Heure'), widget=TimeWidget(), required=False)

    class Meta:
        model = Action
        exclude = ('entity_content_type', 'creation_date', 'validation_date', 'entity_id', 'for_user')

    def __init__(self, entity, *args, **kwargs):
        super(ActionEditForm, self).__init__(*args, **kwargs)
        self.entity = entity
        self.fields['deadline_time'].initial = self.instance.deadline.time() if self.instance.deadline else time()

    def clean(self):
        if self._errors:
            return self.cleaned_data

        cleaned_data = self.cleaned_data

        deadline = cleaned_data.get("deadline")
        deadline_time = cleaned_data.get('deadline_time', time())
        cleaned_data["deadline"] = deadline.replace(hour=deadline_time.hour, minute=deadline_time.minute)

        return cleaned_data
 
    def save (self):
        entity = self.entity

        instance = self.instance
        instance.entity_content_type = entity.entity_type
        instance.entity_id = entity.id

        instance.for_user = self.cleaned_data['user']

        super(ActionEditForm, self).save()


class ActionCreateForm(ActionEditForm):
    def save (self):
        self.instance.creation_date = datetime.today()
        super(ActionCreateForm, self).save()
