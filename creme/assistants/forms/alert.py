# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

from ..models import Alert


# TODO: alright, we need a real date time widget that does this shit !
class AlertForm(CremeModelForm):
    trigger_time = TimeField(label=_('Hour'), required=False)

    class Meta(CremeModelForm.Meta):
        model = Alert
        widgets = {'trigger_date': CalendarWidget}

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance
        instance.creme_entity = entity

        trigger_date = instance.trigger_date

        if trigger_date:
            local_trigger_date = localtime(trigger_date)
            self.fields['trigger_time'].initial = time(
                hour=local_trigger_date.hour,
                minute=local_trigger_date.minute,
            )

    def clean(self):
        cleaned_data = super().clean()

        if not self._errors:
            trigger_time = cleaned_data.get('trigger_time')

            if trigger_time:
                cleaned_data['trigger_date'] = make_aware_dt(
                    datetime.combine(cleaned_data['trigger_date'], trigger_time),
                )

        return cleaned_data
