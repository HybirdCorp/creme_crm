# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from django.forms import IntegerField, BooleanField, CharField
from django.forms.widgets import Textarea
from django.utils.translation import ugettext_lazy as _, ugettext

from creme_core.forms import CremeModelForm

from creme_config.models import SettingKey, SettingValue


_FIELDS = {
        SettingKey.STRING: lambda label: CharField(label=label, widget=Textarea),
        SettingKey.INT:    lambda label: IntegerField(label=label),
        SettingKey.BOOL:   lambda label: BooleanField(label=label, required=False),
    }


class SettingForm(CremeModelForm):
    value = CharField(label=_(u'Value'))

    class Meta:
        model = SettingValue
        exclude = ('key', 'user', 'value_str')

    def __init__(self, *args, **kwargs):
        super(SettingForm, self).__init__(*args, **kwargs)
        fields = self.fields
        svalue = self.instance
        field_class = _FIELDS.get(svalue.key.type)

        if field_class:
            fields['value'] = field_class(ugettext(u'Value'))

        fields['value'].initial = svalue.value

    def save(self, *args, **kwargs):
        self.instance.value = self.cleaned_data['value']
        super(SettingForm, self).save(*args, **kwargs)
