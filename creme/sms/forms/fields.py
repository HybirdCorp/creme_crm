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

from django.forms import RegexField, ValidationError

PHONE_REGEX = r'^[\s]*[\+]{0,1}([\d]+[\s\.\-,]*)+[\s]*$'
PHONE_LIST_REGEX = (
    r'^[\s]*[\+]{0,1}([\d]+[\s\.\-,]*)+[\s]*([%s]{0,1}[\s]*[\+]{0,1}([\d]+[\s\.\-,]*)+[\s]*)*$'
)


class PhoneField(RegexField):
    def __init__(self, *, max_length=None, min_length=None, error_message=None, **kwargs):
        super().__init__(
            regex=PHONE_REGEX,
            max_length=max_length, min_length=min_length,
            error_message=error_message,
            **kwargs
        )

    def clean(self, value):
        value = super().clean(value)

        if value and not self.regex.search(value):
            raise ValidationError(self.error_messages['invalid'])

        return self.filternumbers(value)

    @staticmethod
    def filternumbers(value):
        return ''.join(c for c in value if c.isdigit())


class PhoneListField(RegexField):
    # TODO: rename 'error_message' as 'error_messageS' ?
    def __init__(
            self, *,
            max_length=None, min_length=None, error_message=None, separator='\n',
            **kwargs):
        regex = PHONE_LIST_REGEX % separator
        self.separator = separator

        super().__init__(regex=regex, max_length=max_length, min_length=min_length,
                         error_messages=error_message, **kwargs)

    def clean(self, value):
        value = super().clean(value)

        if value and not self.regex.search(value):
            raise ValidationError(self.error_messages['invalid'])

        return [
            PhoneField.filternumbers(number)
            for number in value.split(self.separator)
        ]
