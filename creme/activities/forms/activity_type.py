################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2023  Hybird
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

from django.utils.translation import gettext_lazy as _

import creme.creme_core.forms.fields as core_fields
from creme.creme_core.forms import CremeModelForm
from creme.creme_core.utils.id_generator import generate_string_id_and_save

from ..models import ActivitySubType, ActivityType


class ActivityTypeForm(CremeModelForm):
    default_hour_duration = core_fields.DurationField(label=_('Duration'))

    class Meta(CremeModelForm.Meta):
        model = ActivityType

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.id:
            self.fields['default_hour_duration'].initial = '0:15:0'

    def save(self):  # TODO: *args, **kwargs
        instance = self.instance

        if not instance.id:
            super().save(commit=False)
            generate_string_id_and_save(
                ActivityType, [instance], 'creme_config-useractivitytype',
            )
        else:
            super().save()

        return instance


class ActivitySubTypeForm(CremeModelForm):
    class Meta(CremeModelForm.Meta):
        model = ActivitySubType

    def save(self, *args, **kwargs):
        instance = self.instance

        if not instance.id:
            super().save(commit=False, *args, **kwargs)
            generate_string_id_and_save(
                ActivitySubType, [instance],
                'creme_config-useractivitydetailesubtype',
            )
        else:
            super().save(*args, **kwargs)

        return instance

    def update_from_widget_response_data(self):
        instance = self.instance

        return {
            'value': str(instance.id),
            'added': [
                {
                    'value': str(instance.id),
                    'label': str(instance),
                    'group': str(instance.type),
                },
            ],
        }
