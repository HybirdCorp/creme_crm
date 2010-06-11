# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.forms.fields import RegexField
from django.forms.util import ValidationError


PHONE_REGEX = '^[\s]*[\+]{0,1}([\d]+[\s\.\-,]*)+[\s]*$'
PHONE_LIST_REGEX = '^[\s]*[\+]{0,1}([\d]+[\s\.\-,]*)+[\s]*([%s]{0,1}[\s]*[\+]{0,1}([\d]+[\s\.\-,]*)+[\s]*)*$'


class PhoneField(RegexField):
    def __init__(self, max_length=None, min_length=None, error_message=None, *args, **kwargs):
        super(PhoneField, self).__init__(PHONE_REGEX, max_length, min_length, error_message, *args, **kwargs)
        
    def clean(self, value):
        value = super(RegexField, self).clean(value)
        
        if value and not self.regex.search(value):
            raise ValidationError(self.error_messages['invalid'])
        
        return PhoneField.filternumbers(value)

    @staticmethod
    def filternumbers(value):
        return ''.join((c for c in value if c.isdigit()))


class PhoneListField(RegexField):
    def __init__(self, max_length=None, min_length=None, error_message=None, separator='\n', *args, **kwargs):
        regex = PHONE_LIST_REGEX % separator
        self.separator = separator
        
        super(PhoneListField, self).__init__(regex, max_length, min_length, error_message, *args, **kwargs)
    
    def clean(self, value):
        value = super(RegexField, self).clean(value)
        
        if value and not self.regex.search(value):
            raise ValidationError(self.error_messages['invalid'])
        
        return [PhoneField.filternumbers(number) for number in value.split(self.separator)]
