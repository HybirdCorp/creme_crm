################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024  Hybird
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

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from creme.activities import get_activity_model
from creme.activities.models import ActivitySubType, Status
from creme.creme_config.forms.fields import CreatorEnumerableModelChoiceField
from creme.creme_core.forms import CremeForm
from creme.creme_core.models import SettingValue

from .. import constants
from ..setting_keys import (
    unsuccessful_duration_key,
    unsuccessful_status_key,
    unsuccessful_subtype_key,
    unsuccessful_title_key,
)

Activity = get_activity_model()


class UnsuccessfulPhoneCallConfigForm(CremeForm):
    sub_type = CreatorEnumerableModelChoiceField(model=Activity, field_name='sub_type')
    title = forms.CharField(
        label=_('Title'),
        max_length=get_activity_model()._meta.get_field('title').max_length,
    )
    status = CreatorEnumerableModelChoiceField(model=Activity, field_name='status')
    duration = forms.IntegerField(
        label=_('Duration (in minutes)'), min_value=1, max_value=120,
        help_text=_('The duration is used to compute automatically the start of the call'),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setting_values = svalues = SettingValue.objects.get_4_keys(
            {'key': unsuccessful_subtype_key},
            {'key': unsuccessful_title_key},
            {'key': unsuccessful_status_key},
            {'key': unsuccessful_duration_key},
        )
        fields = self.fields

        # TODO: add argument "limit_choices_to" to CreatorEnumerableModelChoiceField()?
        sub_type_f = fields['sub_type']
        sub_type_f.enum.enumerator.limit_choices_to = Q(
            type__uuid=constants.UUID_TYPE_PHONECALL,
        )

        try:
            sub_type_f.initial = ActivitySubType.objects.get(
                uuid=svalues[unsuccessful_subtype_key.id].value,
            ).id
        except (ActivitySubType.DoesNotExist, ValidationError):
            pass

        try:
            fields['status'].initial = Status.objects.get(
                uuid=svalues[unsuccessful_status_key.id].value,
            ).id
        except (Status.DoesNotExist, ValidationError):
            pass

        fields['title'].initial = svalues[unsuccessful_title_key.id].value
        fields['duration'].initial = svalues[unsuccessful_duration_key.id].value

    def save(self, commit=True):
        cdata = self.cleaned_data

        svalues = self.setting_values
        svalues[unsuccessful_subtype_key.id].value  = str(cdata['sub_type'].uuid)
        svalues[unsuccessful_title_key.id].value    = cdata['title']
        svalues[unsuccessful_status_key.id].value   = str(cdata['status'].uuid)
        svalues[unsuccessful_duration_key.id].value = cdata['duration']

        # TODO: would be nice to clean the cache of the manager
        #     => set_4_keyS() method?
        SettingValue.objects.bulk_update(svalues.values(), fields=['json_value'])
