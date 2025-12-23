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

# Here are the form-fields which can produce instances of
# <creme_core.core.value_maker.ValueMaker>

from django.forms import HiddenInput, fields
from django.templatetags.tz import localtime
from django.utils.translation import gettext as _

from creme.creme_core.core.value_maker import (
    BooleanMaker,
    DateMaker,
    DateTimeMaker,
    DecimalMaker,
    IntegerMaker,
    NoneMaker,
    StringMaker,
)
from creme.creme_core.forms import fields as core_fields


# TODO: factorise?
class IntegerMakerField(fields.IntegerField):
    def clean(self, value):
        cleaned = super().clean(value)
        return NoneMaker() if cleaned is None else IntegerMaker(cleaned)

    def prepare_value(self, value):
        if isinstance(value, IntegerMaker):
            return value._value  # TODO: better API


class BooleanMakerField(fields.BooleanField):
    def to_python(self, value):
        return BooleanMaker(super().to_python(value))

    def prepare_value(self, value):
        if isinstance(value, BooleanMaker):
            return value._value  # TODO: better API


class DecimalMakerField(fields.DecimalField):
    def clean(self, value):
        cleaned = super().clean(value)
        return NoneMaker() if cleaned is None else DecimalMaker(cleaned)

    def prepare_value(self, value):
        if isinstance(value, DecimalMaker):
            return value._value  # TODO: better API


class StringMakerField(fields.CharField):
    def clean(self, value):
        cleaned = super().clean(value)
        return StringMaker(cleaned) if cleaned else NoneMaker()

    def prepare_value(self, value):
        if isinstance(value, StringMaker):
            return value._str  # TODO: better API


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
                    # NB: the value of return_value is not really used, but
                    #     must be not empty (which is already used by choice "Empty")
                    label=_('Today (dynamic)'), return_value='today', widget=HiddenInput,
                )
            ),
        )

        super().__init__(**kwargs)

    def clean(self, value):
        cleaned = super().clean(value)
        if cleaned:
            match cleaned[0]:
                case self.FIXED:
                    return DateMaker.from_date(cleaned[1])

                case self.TODAY:
                    return DateMaker.from_operator('today')

        return NoneMaker()

    def prepare_value(self, value):
        if isinstance(value, DateMaker):
            date_obj = value._date  # TODO: better API
            return (
                self.TODAY, {self.TODAY: 'today'}
            ) if date_obj is None else (
                self.FIXED, {self.FIXED: date_obj}
            )


class DateTimeMakerField(core_fields.UnionField):
    FIXED = 'fixed'
    NOW = 'now'

    def __init__(self, **kwargs):
        kwargs['empty_label'] = _('No default value')
        kwargs['fields_choices'] = (
            (self.FIXED, fields.DateTimeField(label=_('Fixed date and time'))),
            (
                self.NOW,
                core_fields.ReadonlyMessageField(
                    # NB: the value of return_value is not really used, but
                    #     must be not empty (which is already used by choice "Empty")
                    label=_('Now (dynamic)'), return_value='now', widget=HiddenInput,
                )
            ),
        )

        super().__init__(**kwargs)

    def clean(self, value):
        cleaned = super().clean(value)
        if cleaned:
            match cleaned[0]:
                case self.FIXED:
                    return DateTimeMaker.from_datetime(cleaned[1])

                case self.NOW:
                    return DateTimeMaker.from_operator('now')

        return NoneMaker()

    def prepare_value(self, value):
        if isinstance(value, DateTimeMaker):
            dt = value._dt  # TODO: better API
            return (
                self.NOW, {self.NOW: 'now'}
            ) if dt is None else (
                self.FIXED, {self.FIXED: localtime(dt)}
            )
