################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2025  Hybird
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

from django.forms import HiddenInput, fields
from django.utils.translation import gettext as _

from creme.creme_core.forms import fields as core_fields
from creme.creme_core.gui.custom_field import (
    BooleanMaker,
    DateMaker,
    DecimalMaker,
    IntegerMaker,
    NoneMaker,
    StringMaker,
)


class IntegerMakerField(fields.IntegerField):
    def clean(self, value):
        cleaned = super().clean(value)
        # return NoneMaker() if cleaned is None else IntegerMaker.from_dict({'value': cleaned})
        return NoneMaker() if cleaned is None else IntegerMaker(cleaned)


class BooleanMakerField(fields.BooleanField):
    def to_python(self, value):
        value = super().to_python(value)

        # return BooleanMaker.from_dict({'value': value})
        return BooleanMaker(value)


class DecimalMakerField(fields.DecimalField):
    def clean(self, value):
        cleaned = super().clean(value)
        # return NoneMaker() if cleaned is None else DecimalMaker.from_dict({'value': cleaned})
        return NoneMaker() if cleaned is None else DecimalMaker(cleaned)


class StringMakerField(fields.CharField):
    def clean(self, value):
        cleaned = super().clean(value)
        return StringMaker.from_dict({'value': cleaned}) if cleaned else NoneMaker()


class DateMakerField(core_fields.UnionField):
    FIXED = 'fixed'
    TODAY = 'today'

    def __init__(self, **kwargs):
        kwargs['empty_label'] = _('No default value')
        kwargs['fields_choices'] = (
            (self.FIXED, fields.DateField(label=_('Fixed date'))),
            (
                self.TODAY,
                core_fields.ReadonlyMessageField(
                    label=_('Today (dynamic)'), return_value='today', widget=HiddenInput,
                )
            ),
        )

        super().__init__(**kwargs)

    def clean(self, value):
        from creme.creme_core.utils.dates import date_to_ISO8601

        cleaned = super().clean(value)
        if cleaned:
            # TODO: DateMaker.from_date() ?
            match cleaned[0]:
                case self.FIXED:
                    return DateMaker.from_dict({'value': date_to_ISO8601(cleaned[1])})

                case self.TODAY:
                    return DateMaker.from_dict({'op': 'today'})

        return NoneMaker()

# TODO:
#   class DatetimeMakerField(core_fields.UnionField):
