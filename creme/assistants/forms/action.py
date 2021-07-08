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

from datetime import datetime, time

from django.forms.fields import TimeField
from django.utils.timezone import localtime
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms import CremeModelForm
from creme.creme_core.forms.widgets import CalendarWidget
from creme.creme_core.utils.dates import make_aware_dt

from ..models import Action


# TODO: alright, we need a real date time widget that does this shit !
class ActionForm(CremeModelForm):
    deadline_time = TimeField(label=_('Hour'), required=False)

    class Meta(CremeModelForm.Meta):
        model = Action
        widgets = {'deadline': CalendarWidget}

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance
        instance.creme_entity = entity

        deadline = instance.deadline

        if deadline:
            local_deadline = localtime(deadline)
            self.fields['deadline_time'].initial = time(
                hour=local_deadline.hour, minute=local_deadline.minute,
            )

    def clean(self):
        cdata = super().clean()

        if not self._errors:
            deadline_time = cdata.get('deadline_time')

            if deadline_time:
                cdata['deadline'] = make_aware_dt(
                    datetime.combine(cdata['deadline'], deadline_time)
                )

        return cdata
