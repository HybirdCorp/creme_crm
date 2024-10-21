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
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms.base import CremeModelForm

from ..models import NumberGeneratorItem


class NumberGeneratorItemEditionForm(CremeModelForm):
    class Meta:
        model = NumberGeneratorItem
        fields = ('is_edition_allowed',)


class RegularNumberGeneratorItemEditionForm(NumberGeneratorItemEditionForm):
    format = forms.CharField(label=_('Pattern'))  # TODO: help text
    reset = forms.ChoiceField(
        label=_('Reset the counter'),
        # TODO "number"?
        help_text=_('When the counter ({number} in the pattern) should be reset?'),
        required=False,  # TODO: remove + ''=>'never'??
        # TODO: use an enum + factorise w/ generator
        choices=[
            ('',        _('Never')),  # TODO: pgettext()
            ('monthly', _('Monthly')),
            ('yearly',  _('Yearly')),
        ]
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        data = self.instance.data
        fields = self.fields

        fields['format'].initial = data['format']
        fields['reset'].initial = data.get('reset', '')

    def save(self, *args, **kwargs):
        cleaned = self.cleaned_data
        data = self.instance.data
        data['format'] = cleaned['format']
        data['reset']  = cleaned['reset']
        return super().save(*args, **kwargs)
