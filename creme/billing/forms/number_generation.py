################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024-2025  Hybird
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

import re

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme.creme_core.forms.base import CremeModelForm
from creme.creme_core.forms.fields import ReadonlyMessageField
from creme.creme_core.forms.widgets import PrettySelect
from creme.creme_core.gui.bulk_update import FieldOverrider

from ..models import NumberGeneratorItem


# Inner-edition ----------------------------------------------------------------
class NumberOverrider(FieldOverrider):
    field_names = ['number']

    error_messages = {
        'configuration': _('The number is set as not editable by the configuration.'),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._item = None

    def formfield(self, instances, user, **kwargs):
        first = instances[0]
        model_field = type(first)._meta.get_field(self.field_names[0])

        # TODO: prefetch <source> for <instances>
        self._item = item = NumberGeneratorItem.objects.get_for_instance(first)

        if item and not item.is_edition_allowed:
            return ReadonlyMessageField(
                label=model_field.verbose_name,
                initial=self.error_messages['configuration'],
            )

        number_field = model_field.formfield()

        if len(instances) == 1:
            number_field.initial = first.number

        return number_field

    def post_clean_instance(self, *, instance, value, form):
        item = self._item
        if item and not item.is_edition_allowed:
            raise ValidationError(
                self.error_messages['configuration'],
                code='configuration',
            )

        # TODO: default implementation of post_clean_instance()?
        setattr(instance, self.field_names[0], value)


# Configuration ----------------------------------------------------------------
class NumberGeneratorItemEditionForm(CremeModelForm):
    class Meta:
        model = NumberGeneratorItem
        fields = ('is_edition_allowed',)


class RegularNumberGeneratorItemEditionForm(NumberGeneratorItemEditionForm):
    format = forms.CharField(
        # Translators: the pattern is a format string used to build a number
        label=pgettext_lazy('billing-number-generator', 'Pattern'),
        help_text=_(
            'These variables are available:\n'
            ' - {counter} is a number which is automatically incremented when a '
            'generation is done. You can use the syntax {counter:0X} to pad the '
            'number with zeros (e.g. "{counter:04}" will produce "0006" for six). '
            'You MUST use this variable.\n'
            ' - {year} & {month} use the current date of the generation.\n'
            ' - {code} uses the field «code» of the emitter Organisation.'
        ),
        # NB: Base.number.max_length == 100. We keep a margin to avoid IntegrityError
        #     (e.g. Organisation.code could be very long).
        #     Not perfect but should be sufficient...
        max_length=50,
    )
    reset = forms.ChoiceField(
        label=_('Reset the counter'),
        help_text=_('When the counter («{counter}» in the pattern) should be reset?'),
        widget=PrettySelect,
        # choices=...  => See below
    )
    counter = forms.IntegerField(
        label=_('Current counter'),
        help_text=_(
            'Current value of the counter (will be used to generate the NEXT number).\n'
            'Tip: modify this value only if you know what you do; it can be useful '
            'after having imported entities from a CSV/XLS file which contains '
            'numbers, in order to keep a consistent numbering.',
        ),
        min_value=1,
    )

    # TODO: better system to share constraints with generator
    extra_variables = {'year', 'month', 'code'}

    def __init__(self, *args, **kwargs):
        from ..number_generators import ResetType

        super().__init__(*args, **kwargs)
        data = self.instance.data
        fields = self.fields

        fields['format'].initial = data['format']
        fields['counter'].initial = data.get('counter', 1)

        reset_f = fields['reset']
        reset_f.choices = ResetType.choices
        reset_f.initial = data['reset']

    def clean_format(self):
        format_str = self.cleaned_data['format']
        counter_found = False

        for var in re.findall(pattern='{(.*?)}', string=format_str):
            if not var:
                raise ValidationError(gettext('The empty variable «{}» is forbidden.'))
            elif re.match(pattern='^counter(:0[1-9])?', string=var):
                counter_found = True
            elif var not in self.extra_variables:
                raise ValidationError(
                    gettext('The variable «{name}» is invalid.').format(name=var),
                )

        if not counter_found:
            raise ValidationError(gettext('You must use the variable «{counter}».'))

        return format_str

    def clean(self):
        from ..number_generators import ResetType

        cdata = super().clean()

        if not self._errors:
            format_str = cdata['format']
            reset = cdata['reset']

            if reset == ResetType.YEARLY:
                if '{year}' not in format_str:
                    self.add_error(
                        field='format',
                        error=gettext(
                            'You must use the variable «{year}» if you want to '
                            'reset the counter each year.'
                        ),
                    )
            elif reset == ResetType.MONTHLY:
                if '{month}' not in format_str:
                    self.add_error(
                        field='format',
                        error=gettext(
                            'You must use the variable «{month}» if you want to '
                            'reset the counter each month.'
                        ),
                    )
                if '{year}' not in format_str:
                    self.add_error(
                        field='format',
                        error=gettext(
                            'You must use the variable «{year}» if you want to '
                            'reset the counter each month.'
                        ),
                    )

        return cdata

    def save(self, *args, **kwargs):
        cleaned = self.cleaned_data
        data = self.instance.data
        data['format']  = cleaned['format']
        data['reset']   = cleaned['reset']
        data['counter'] = cleaned['counter']

        return super().save(*args, **kwargs)
