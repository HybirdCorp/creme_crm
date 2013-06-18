# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from django.utils.timezone import now, localtime
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.forms import CremeModelWithUserForm, CremeDateTimeField, CremeTimeField
from creme.creme_core.utils.dates import make_aware_dt

from ..models import Action


#TODO: alright, we need a real date time widget that this shit !
class ActionEditForm(CremeModelWithUserForm):
    deadline      = CremeDateTimeField(label=_(u"Deadline"))
    deadline_time = CremeTimeField(label=_(u'Hour'), required=False)

    class Meta:
        model = Action

    def __init__(self, entity, *args, **kwargs):
        super(ActionEditForm, self).__init__(*args, **kwargs)
        self.entity = entity

        #deadline = self.instance.deadline
        #self.fields['deadline_time'].initial = deadline.time() if deadline else time()
        deadline = localtime(self.instance.deadline)
        self.fields['deadline_time'].initial = time(hour=deadline.hour,
                                                    minute=deadline.minute,
                                                   ) if deadline else time()

    def clean(self):
        if self._errors:
            return self.cleaned_data

        cleaned_data = self.cleaned_data

        #deadline = cleaned_data.get("deadline")
        #deadline_time = cleaned_data.get('deadline_time') or time()
        #cleaned_data["deadline"] = deadline.replace(hour=deadline_time.hour, minute=deadline_time.minute)

        deadline_time = cleaned_data.get('deadline_time')
        if deadline_time:
            cleaned_data['deadline'] = make_aware_dt(datetime.combine(cleaned_data['deadline'], deadline_time))

        return cleaned_data

    def save(self, *args, **kwargs):
        self.instance.creme_entity = self.entity
        return super(ActionEditForm, self).save(*args, **kwargs)


class ActionCreateForm(ActionEditForm):
    def save(self, *args, **kwargs):
        #self.instance.creation_date = datetime.today()
        self.instance.creation_date = now()
        return super(ActionCreateForm, self).save(*args, **kwargs)
