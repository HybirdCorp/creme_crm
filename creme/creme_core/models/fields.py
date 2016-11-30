# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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

from json import loads as jsonloads, dumps as jsondumps

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import (DateTimeField, CharField, TextField, DecimalField,
        PositiveIntegerField, OneToOneField, ForeignKey, SET, Max)
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from ..core import validators
from ..utils.date_period import date_period_registry, DatePeriod


# TODO: add a form field ?? (validation)
# TODO: fix the max_lenght value ?,
class PhoneField(CharField):
    pass


# TODO: Make a real api for this
class DurationField(CharField):
    pass


class UnsafeHTMLField(TextField):
    pass


class ColorField(CharField):
    default_validators = [validators.validate_color]
    description = _('HTML Color')

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 6
        super(ColorField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        from ..forms.fields import ColorField as ColorFormField  # Lazy loading

        defaults = {'form_class': ColorFormField}
        defaults.update(kwargs)

        return super(CharField, self).formfield(**defaults)


class DatePeriodField(TextField):  # TODO: inherit from a JSONField
    def to_python(self, value):
        if not value:  # if value is None: ??
            return None

        if isinstance(value, basestring):
            return date_period_registry.deserialize(jsonloads(value))

        # DatePeriod instance
        return value

    def from_db_value(self, value, expression, connection, context):
        if value is None:
            return None

        # 'basestring' instance
        return date_period_registry.deserialize(jsonloads(value))

    def get_db_prep_value(self, value, connection, prepared=False):
        if value is None:
            return None

        if not isinstance(value, DatePeriod):
            raise ValueError('DatePeriodField: value must be a DatePeriod')

        return jsondumps(value.as_dict())

    def formfield(self, **kwargs):
        from ..forms.fields import DatePeriodField as DatePeriodFormField  # Lazy loading

        defaults = {'form_class': DatePeriodFormField}
        defaults.update(kwargs)

        # Beware we do not call TextField.formfield because it overload 'widget'
        # (we could define the 'widget' key in 'defaults'...)
        return super(TextField, self).formfield(**defaults)


class MoneyField(DecimalField):
    pass


def _transfer_assignation():
    return CremeUserForeignKey._TRANSFER_TO_USER


class CremeUserForeignKey(ForeignKey):
    _TRANSFER_TO_USER = None

    def __init__(self, **kwargs):
        kwargs['limit_choices_to'] = {'is_staff': False}
        # Override on_delete, even if it was already defined in kwargs
        kwargs['on_delete'] = SET(_transfer_assignation)
        kwargs.setdefault('to', settings.AUTH_USER_MODEL)
        super(CremeUserForeignKey, self).__init__(**kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(CremeUserForeignKey, self).deconstruct()

        kwargs.pop('limit_choices_to', None)
        del kwargs['on_delete']

        return name, path, args, kwargs

    def get_internal_type(self):
        return "ForeignKey"


class CTypeForeignKey(ForeignKey):
    def __init__(self, **kwargs):
        kwargs['to'] = ContentType
        super(CTypeForeignKey, self).__init__(**kwargs)

    def __get__(self, instance, instance_type=None):
        ct_id = getattr(instance, self.attname)
        return ContentType.objects.get_for_id(ct_id) if ct_id else None

    def __set__(self, instance, value):
        # TODO: accept model directly + get_for_model() ??
        setattr(instance, self.attname, value.id if value else value)

    # def contribute_to_class(self, cls, name):
    def contribute_to_class(self, cls, name, **kwargs):
        super(CTypeForeignKey, self).contribute_to_class(cls, name, **kwargs)

        # Connect self as the descriptor for this field (thx to GenericForeignKey code)
        setattr(cls, name, self)

    def deconstruct(self):
        name, path, args, kwargs = super(CTypeForeignKey, self).deconstruct()
        # kwargs.pop('to', None)

        return name, path, args, kwargs

    # TODO: factorise
    def get_internal_type(self):
        return "ForeignKey"

    def formfield(self, **kwargs):
        from ..forms.fields import CTypeChoiceField
        defaults = {'form_class': CTypeChoiceField}
        defaults.update(kwargs)

        # Beware we don't call super(CTypeForeignKey, self).formfield(**defaults)
        # to avoid useless/annoying 'queryset' arg
        return super(ForeignKey, self).formfield(**defaults)


class EntityCTypeForeignKey(CTypeForeignKey):
    # TODO: assert that it is a CremeEntity instance ??
    # def __set__(self, instance, value):
    #     setattr(instance, self.attname, value.id if value else value)

    def formfield(self, **kwargs):
        from ..forms.fields import EntityCTypeChoiceField
        defaults = {'form_class': EntityCTypeChoiceField}
        defaults.update(kwargs)
        return super(EntityCTypeForeignKey, self).formfield(**defaults)


# TODO: factorise with CTypeForeignKey
class CTypeOneToOneField(OneToOneField):
    def __init__(self, **kwargs):
        kwargs['to'] = ContentType
        super(CTypeOneToOneField, self).__init__(**kwargs)

    def __get__(self, instance, instance_type=None):
        ct_id = getattr(instance, self.attname)
        return ContentType.objects.get_for_id(ct_id) if ct_id else None

    def __set__(self, instance, value):
        # TODO: accept model directly + get_for_model() ??
        setattr(instance, self.attname, value.id if value else value)

    # def contribute_to_class(self, cls, name):
    def contribute_to_class(self, cls, name, **kwargs):
        super(CTypeOneToOneField, self).contribute_to_class(cls, name, **kwargs)

        # Connect self as the descriptor for this field (thx to GenericForeignKey code)
        setattr(cls, name, self)

    def deconstruct(self):
        name, path, args, kwargs = super(CTypeOneToOneField, self).deconstruct()
        # kwargs.pop('to', None)

        return name, path, args, kwargs

    def get_internal_type(self):
        return "OneToOneField"

    def formfield(self, **kwargs):
        from ..forms.fields import CTypeChoiceField
        defaults = {'form_class': CTypeChoiceField}
        defaults.update(kwargs)

        # Beware we don't call super(CTypeOneToOneField, self).formfield(**defaults)
        # to avoid useless/annoying 'queryset' arg
        return super(OneToOneField, self).formfield(**defaults)


class BasicAutoField(PositiveIntegerField):
    """BasicAutoField is a PositiveIntegerField which uses an auto-incremented
    value when no value is given.

    Notice that that the method is really simple, so the limits are :
        - The value is the maximum value plus one, so it does not remember the deleted maximum values.
        - There could be a race condition on the maximum computing.

    This field is OK for 'order' in ordered model as creme_config wants them because:
        - creme_config fixes the order problems (duplication, 'hole').
        - order are principally use by GUI, and are not a business constraint.
    """
    def __init__(self, *args, **kwargs):
        setdefault = kwargs.setdefault
        setdefault('editable', False)
        setdefault('blank',    True)

        # Not '1', in order to distinguish a initialised value from a non initialised one.
        kwargs['default'] = None

        super(BasicAutoField, self).__init__(*args, **kwargs)
        self.set_tags(viewable=False)

    def deconstruct(self):
        name, path, args, kwargs = super(BasicAutoField, self).deconstruct()

        if self.editable:
            kwargs['editable'] = True

        if not self.blank:
            kwargs['blank'] = False

        del kwargs['default']

        return name, path, args, kwargs

    def pre_save(self, model, add):
        attname = self.attname
        value = getattr(model, attname, None)

        if add and value is None:
            aggr = model.__class__.objects.aggregate(Max(attname))
            value = (aggr[attname + '__max'] or 0) + 1

            setattr(model, attname, value)

        return value


# Code copied/modified from django_extensions one:
#    http://code.google.com/p/django-command-extensions/

################################################################################
#  Copyright (c) 2007  Michael Trier
#  Copyright (C) 2014  http://trbs.net
#  Copyright (C) 2009-2015  Hybird
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#  THE SOFTWARE.
################################################################################

class CreationDateTimeField(DateTimeField):
    """ CreationDateTimeField

    By default, sets editable=False, blank=True, default=now
    """
    def __init__(self, *args, **kwargs):
        setdefault = kwargs.setdefault
        setdefault('editable', False)
        setdefault('blank',    True)
        setdefault('default',  now)

        super(CreationDateTimeField, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return "DateTimeField"

    def deconstruct(self):
        name, path, args, kwargs = super(CreationDateTimeField, self).deconstruct()

        if self.editable:
            kwargs['editable'] = True

        if not self.blank:
            kwargs['blank'] = False

        if self.default is not now:
            kwargs['default'] = self.default

        return name, path, args, kwargs


class ModificationDateTimeField(CreationDateTimeField):
    """ ModificationDateTimeField

    By default, sets editable=False, blank=True, default=now

    Sets value to now() on each save of the model.
    """
    def pre_save(self, model, add):
        value = now()
        setattr(model, self.attname, value)

        return value
