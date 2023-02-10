################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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

from functools import partial

from django.forms import (
    BooleanField,
    CharField,
    ChoiceField,
    EmailField,
    IntegerField,
)
from django.forms.widgets import Textarea
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.setting_key import SettingKey
from creme.creme_core.forms import CremeForm, CremeModelForm
from creme.creme_core.models import SettingValue

_FIELDS = {
    SettingKey.STRING: lambda label: CharField(label=label, widget=Textarea),
    SettingKey.INT:    IntegerField,
    SettingKey.BOOL:   lambda label: BooleanField(label=label, required=False),
    # TODO: an HourField inheriting ChoiceField ?? (+factorise with 'polls')
    SettingKey.HOUR:   lambda label: IntegerField(label=label, min_value=0, max_value=23),
    SettingKey.EMAIL:  EmailField,
}


def get_setting_value_field(key, initial):
    choices = key.choices

    if choices:
        field_class = partial(ChoiceField, choices=choices)
    else:
        field_class = _FIELDS.get(key.type)

    return field_class(
        label=gettext('Value'),
        initial=initial,
    ) if field_class else None


class SettingForm(CremeModelForm):
    value = CharField(label=_('Value'))

    class Meta:
        model = SettingValue
        exclude = ('key_id', 'user', 'value_str')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fields = self.fields
        svalue = self.instance

        value_f = fields['value'] = get_setting_value_field(
            key=svalue.key,
            initial=fields['value'].initial
        )

        # We avoid "value_f.required = not svalue.key.blank" because BooleanField is never required
        if svalue.key.blank:
            value_f.required = value_f.widget.is_required = False

    def save(self, *args, **kwargs):
        self.instance.value = self.cleaned_data['value']

        return super().save(*args, **kwargs)


class UserSettingForm(CremeForm):
    value = CharField(label=_('Value'))

    def __init__(self, skey, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.skey = skey
        fields = self.fields
        value_f = fields['value'] = get_setting_value_field(
            key=skey,
            initial=fields['value'].initial
        )

        try:
            value_f.initial = self.user.settings[skey]
        except KeyError:
            pass

        # We avoid "value_f.required = not svalue.key.blank" because BooleanField is never required
        if skey.blank:
            value_f.required = value_f.widget.is_required = False

    def save(self, *args, **kwargs):
        c_value = self.cleaned_data['value']

        with self.user.settings as settings:
            if c_value is None:
                del settings[self.skey]
            else:
                settings[self.skey] = c_value
