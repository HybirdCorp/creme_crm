# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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
from django.core import checks
from django.core.exceptions import FieldDoesNotExist
from django.db.models import (DateTimeField, CharField, TextField, DecimalField,
        PositiveIntegerField, OneToOneField, ForeignKey, SET, CASCADE, Max)
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from ..core import validators
from ..utils.date_period import date_period_registry, DatePeriod


# TODO: add a form field ?? (validation)
# TODO: fix the max_length value ?,
class PhoneField(CharField):
    pass


# TODO: Make a real API for this
class DurationField(CharField):
    pass


class UnsafeHTMLField(TextField):
    pass


class ColorField(CharField):
    default_validators = [validators.validate_color]
    description = _('HTML Color')

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 6  # TODO: accepts 8 too (if alpha is needed) ?
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        from ..forms.fields import ColorField as ColorFormField  # Lazy loading

        defaults = {'form_class': ColorFormField}
        defaults.update(kwargs)

        return super().formfield(**defaults)


class DatePeriodField(TextField):  # TODO: inherit from a JSONField
    def to_python(self, value):
        if not value:  # if value is None: ??
            return None

        if isinstance(value, str):
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

        # BEWARE: we do not call TextField.formfield because it overload 'widget'
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
        super().__init__(**kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()

        kwargs.pop('limit_choices_to', None)
        del kwargs['on_delete']

        return name, path, args, kwargs

    def get_internal_type(self):
        return 'ForeignKey'


class CTypeForeignKey(ForeignKey):
    def __init__(self, **kwargs):
        kwargs['to'] = 'contenttypes.ContentType'
        # In a normal use, ContentType instances are never deleted ; so CASCADE by default should be OK
        kwargs.setdefault('on_delete', CASCADE)
        super().__init__(**kwargs)

    def __get__(self, instance, instance_type=None):
        ct_id = getattr(instance, self.attname)
        return ContentType.objects.get_for_id(ct_id) if ct_id else None

    def __set__(self, instance, value):
        # TODO: accept model directly + get_for_model() ??
        setattr(instance, self.attname, value.id if value else value)

    def contribute_to_class(self, cls, name, **kwargs):
        super().contribute_to_class(cls, name, **kwargs)

        # Connect self as the descriptor for this field (thx to GenericForeignKey code)
        setattr(cls, name, self)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        # kwargs.pop('to', None)

        return name, path, args, kwargs

    # TODO: factorise
    def get_internal_type(self):
        return 'ForeignKey'

    def formfield(self, **kwargs):
        from ..forms.fields import CTypeChoiceField
        defaults = {'form_class': CTypeChoiceField}
        defaults.update(kwargs)

        # BEWARE: we don't call super(CTypeForeignKey, self).formfield(**defaults)
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

        return super().formfield(**defaults)


# TODO: factorise with CTypeForeignKey
class CTypeOneToOneField(OneToOneField):
    def __init__(self, **kwargs):
        kwargs['to'] = 'contenttypes.ContentType'

        # In a normal use, ContentType instances are never deleted ; so CASCADE by default should be OK
        kwargs.setdefault('on_delete', CASCADE)

        super().__init__(**kwargs)

    def __get__(self, instance, instance_type=None):
        ct_id = getattr(instance, self.attname)
        return ContentType.objects.get_for_id(ct_id) if ct_id else None

    def __set__(self, instance, value):
        # TODO: accept model directly + get_for_model() ??
        setattr(instance, self.attname, value.id if value else value)

    def contribute_to_class(self, cls, name, **kwargs):
        super().contribute_to_class(cls, name, **kwargs)

        # Connect self as the descriptor for this field (thx to GenericForeignKey code)
        setattr(cls, name, self)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        # kwargs.pop('to', None)

        return name, path, args, kwargs

    def get_internal_type(self):
        return 'OneToOneField'

    def formfield(self, **kwargs):
        from ..forms.fields import CTypeChoiceField
        defaults = {'form_class': CTypeChoiceField}
        defaults.update(kwargs)

        # BEWARE: we don't call super(CTypeOneToOneField, self).formfield(**defaults)
        # to avoid useless/annoying 'queryset' arg
        return super(OneToOneField, self).formfield(**defaults)


class RealEntityForeignKey:
    """ Provide a "virtual" field which uses & combines 2 ForeignKeys :
     - a ForeignKey to CremeEntity.
     - a ForeignKey to ContentType (tips: it work  well with a EntityCTypeForeignKey).

    So it can directly reference an instance of class inheriting CremeEntity
    (what we call "real entity").

    It allows to :
     - get the real entity with only 1 query  (a simple ForeignKey to CremeEntity
       will retrieve a CremeEntity, then .get_real_entity() will perform a second query).
     - set the 2 FKs at once.

    Unlike GenericForeignKey, the ID if the CremeEntity is stored in a real ForeignKey  ;
    so we can perform classical filters on this ForeignKey that we could not perform
    with a PositiveIntegerField.
    """
    # Field flags
    auto_created = False
    concrete = False
    editable = False
    hidden = False

    is_relation = True
    many_to_many = False
    many_to_one = True
    one_to_many = False
    one_to_one = False
    related_model = None
    remote_field = None

    def __init__(self, ct_field, fk_field):
        self._ct_field_name = ct_field
        self._fk_field_name = fk_field

        # TODO ?
        # self.rel = None
        # self.column = None

        self.name = None
        self.model = None
        self.cache_attr = None

    def __str__(self):
        model = self.model

        return '{}.{}.{}'.format(
            model._meta.app_label,
            model._meta.object_name,
            self.name,
        )

    def contribute_to_class(self, cls, name, **kwargs):
        self.name = name
        self.model = cls
        self.cache_attr = '_{}_cache'.format(name)
        cls._meta.add_field(self, private=True)  # TODO: test ?
        setattr(cls, name, self)

    def check(self, **kwargs):
        from .entity import CremeEntity

        errors = []
        errors.extend(self._check_field_name())
        errors.extend(self._check_fk('_ct_field_name', ContentType))
        errors.extend(self._check_fk('_fk_field_name', CremeEntity))

        return errors

    def _check_field_name(self):
        if self.name.endswith('_'):
            yield checks.Error('Field names must not end with an underscore.',
                               obj=self,
                               id='fields.E001',
                              )

    def _check_fk(self, attr_name, related_model):
        fname = getattr(self, attr_name)
        meta = self.model._meta

        try:
            field = meta.get_field(fname)
        except FieldDoesNotExist:
            yield checks.Error(
                'The RealEntityForeignKey references the non-existent field "{}".'.format(fname),
                obj=self,
                id='creme.E007',
            )
        else:
            if not isinstance(field, ForeignKey):
                yield checks.Error(
                    '"{}.{}" is not a ForeignKey.'.format(meta.object_name, fname),
                    obj=self,
                    id='creme.E007',
                )
            elif field.remote_field.model != related_model:
                rel_meta = related_model._meta

                yield checks.Error(
                    '"{}.{}" is not a ForeignKey to "{}.{}".'.format(
                        meta.object_name, fname, rel_meta.app_label, rel_meta.object_name
                    ),
                    obj=self,
                    id='creme.E007',
                )

    @staticmethod
    def _ctype_or_die(ct):
        if ct is None:
            raise ValueError('The content type is not set while the entity is. '
                             'HINT: set both by hand or just use the RealEntityForeignKey setter.'
                            )

    def __get__(self, instance, cls=None):
        # TODO ?
        # if instance is None:
        #     return self

        real_entity = getattr(instance, self.cache_attr, None)

        if real_entity is None:
            get_field = self.model._meta.get_field

            # NB:  <ct = getattr(instance, self._ct_field_name)> will perform an additional
            # query if the field is not a (Entity)CTypeForeignKey instance.  TODO: unit test
            ct_field = get_field(self._ct_field_name)
            ct_id = getattr(instance, ct_field.get_attname())
            ct = ContentType.objects.get_for_id(ct_id) if ct_id else None

            fk_field = get_field(self._fk_field_name)
            fk_cache_name = fk_field.get_cache_name()

            if hasattr(instance, fk_cache_name):
                entity = getattr(instance, fk_cache_name)

                if entity is None:
                    real_entity = None
                else:
                    self._ctype_or_die(ct)

                    if entity.entity_type_id != ct.id:
                        raise ValueError('The content type does not match this entity.')

                    real_entity = entity.get_real_entity()
            else:
                entity_id = getattr(instance, fk_field.get_attname())

                if entity_id is None:
                    real_entity = None
                else:
                    self._ctype_or_die(ct)

                    real_entity = ct.model_class()._default_manager.get(id=entity_id)

            setattr(instance, self.cache_attr, real_entity)

        return real_entity

    def __set__(self, instance, value):
        ct = None

        if value is not None:
            ct = value.entity_type

        setattr(instance, self._ct_field_name, ct)
        setattr(instance, self._fk_field_name, value)
        # setattr(instance, self.cache_attr, value)  # We use the cache of FK/entity instead.


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

        super().__init__(*args, **kwargs)
        self.set_tags(viewable=False)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()

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
#  Copyright (C) 2009-2018  Hybird
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

        super().__init__(*args, **kwargs)

    def get_internal_type(self):
        return 'DateTimeField'

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()

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
