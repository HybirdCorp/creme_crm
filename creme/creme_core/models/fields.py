################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from collections import defaultdict
from json import loads as json_load

from django import forms
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core import checks
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db import models
from django.db.models.aggregates import Max
from django.db.models.deletion import CASCADE, SET
from django.db.models.fields import Field
from django.db.models.fields.mixins import FieldCacheMixin
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from ..core import validators
from ..core.field_tags import FieldTag
from ..utils.color import random_pastel_color
from ..utils.date_period import DatePeriod, date_period_registry
from ..utils.serializers import json_encode


class SemanticCharField(models.CharField):
    # NOTE: the attribute must be overridden BEFORE the forms are built
    #       (so the hooking app must be before the hooked app in INSTALLED_APPS)
    # TODO: create "lazy" field (with an inner field)?
    formfield_class = None

    def formfield(self, form_class=None, **kwargs):
        return super().formfield(form_class=form_class or self.formfield_class, **kwargs)


# TODO: add a form field? (validation)
# TODO: fix the max_length value?
class PhoneField(SemanticCharField):
    pass


# TODO: make a real API for this (accept timedelta as value etc...)
# TODO: formfield()
# TODO: IntegerField (number of seconds?)?
class DurationField(models.CharField):
    pass


class IntegerPercentField(models.PositiveIntegerField):
    def formfield(self, **kwargs):
        from ..forms import fields as form_fields

        return super().formfield(**{
            'form_class': form_fields.IntegerPercentField,
            'min_value': 0,
            'max_value': 100,
            **kwargs
        })


class DecimalPercentField(models.DecimalField):
    def __init__(self,
                 verbose_name=None,
                 name=None,
                 max_digits=4,
                 decimal_places=2,
                 **kwargs,
                 ):
        super().__init__(
            verbose_name=verbose_name,
            name=name,
            max_digits=max_digits,
            decimal_places=decimal_places,
            **kwargs
        )

    def formfield(self, **kwargs):
        from ..forms import fields as form_fields

        return super().formfield(**{
            'form_class': form_fields.DecimalPercentField,
            'min_value': 0,
            'max_value': 100,
            **kwargs
        })


class YearField(models.PositiveIntegerField):
    def formfield(self, **kwargs):
        from ..forms import fields as form_fields

        return super().formfield(**{
            'form_class': form_fields.YearField,
            **kwargs
        })


class FileSizeField(models.PositiveIntegerField):
    pass


class MoneyField(models.DecimalField):
    pass


class UnsafeHTMLField(models.TextField):
    pass


class CremeURLField(models.CharField):
    """URLField which does not validate the URL validity.
    URL validation is hard:
     - The Django's validator does not work with local URLs without domain
     - The Django's validator wants a protocol (https, https), but data imported
       data (from CSV, .xls, ...) generally does not have a protocol, causing
       import errors. We could add a protocol, but which one?
     - etc...
    So this field exists only to get a cool display of the data (i.e. <a> tag).
    """
    default_validators = []  # NOPE
    description = _('URL (no validation)')


class ColorField(models.CharField):
    default_validators = [validators.validate_color]
    description = _('HTML Color')

    def __init__(self, verbose_name=_('Color'), *args, **kwargs):
        kwargs['max_length'] = 6  # TODO: accepts 8 too (if alpha is needed) ?
        super().__init__(verbose_name=verbose_name, *args, **kwargs)

    @staticmethod
    def random():
        return random_pastel_color().html[1:]

    def formfield(self, **kwargs):
        from ..forms.fields import ColorField as ColorFormField  # Lazy loading

        return super().formfield(**{'form_class': ColorFormField, **kwargs})


class DatePeriodField(models.TextField):  # TODO: inherit from JSONField?
    """Field which stores a 'creme_core.utils.date_period.DatePeriod'.
    Internally the period is stored as a JSON dictionary (the dictionary is
    built by 'DatePeriod.as_dict()').

    The field accepts these kind of value :
        - None (the field should be declared as 'null=True' of course).
        - DatePeriod instance (hint: retrieve them with
          'creme_core.utils.date_period.date_period_registry.get_period()' to be
          sure the period you want is correct).
          Notice that it cannot be used as 'default' value directly (not serializable),
          but you can call the method 'DatePeriod.as_dict()'.
        - dictionary, like the ones 'DatePeriod.as_dict()' generates
          (e.g. {'type': 'days', 'value': 1}).
    """
    def to_python(self, value) -> DatePeriod | None:
        if not value:
            return None

        if isinstance(value, dict):
            try:
                period = date_period_registry.deserialize(value)
            except KeyError as e:
                raise ValidationError(
                    f'{type(self).__name__}.to_python(): dict is invalid (missing key {e})'
                ) from e

            # NB: the dict was not empty (see guard at the beginning),
            #     so <None> means there is an error.
            if period is None:
                raise ValidationError(
                    f'{type(self).__name__}.to_python(): period is invalid (dict argument)'
                )

            return period

        # NB: seems not very useful
        # if isinstance(value, str):
        #     try:
        #         period = date_period_registry.deserialize(json_load(value))
        #     except JSONDecodeError as e:
        #         raise ValidationError(
        #             f'DatePeriodField.to_python(): invalid JSON ({e})'
        #         ) from e
        #     except KeyError as e:
        #         raise ValidationError(
        #             f'DatePeriodField.to_python(): string is invalid (missing key {e})'
        #         ) from e
        #
        #     if period is None:
        #         raise ValidationError(
        #             'DatePeriodField.to_python(): period is invalid (string argument)'
        #         )
        #
        #     return period

        if isinstance(value, DatePeriod):
            return value

        raise ValidationError(
            f"{type(self).__name__}.to_python(): "
            f"value must be None/dict/string/DatePeriod ('{type(value).__name__}' given)"
        )

    def from_db_value(self, value, expression, connection):
        return None if value is None else date_period_registry.deserialize(json_load(value))

    def get_prep_value(self, value):
        return self.to_python(super().get_prep_value(value))

    def get_db_prep_value(self, *args, **kwargs):
        prep_value = super().get_db_prep_value(*args, **kwargs)

        return None if prep_value is None else json_encode(prep_value.as_dict())

    def formfield(self, **kwargs):
        # Lazy loading
        from ..forms.fields import DatePeriodField as DatePeriodFormField

        # BEWARE: we do not call TextField.formfield because it overrides 'widget'
        # (we could define the 'widget' key in 'defaults'...)
        return super(
            models.TextField, self,
        ).formfield(**{'form_class': DatePeriodFormField, **kwargs})


def _transfer_assignation():
    return CremeUserForeignKey._TRANSFER_TO_USER


class CremeUserForeignKey(models.ForeignKey):
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

    def formfield(self, **kwargs):
        from ..forms import fields as core_fields

        if self.get_tag(FieldTag.ENUMERABLE):
            return Field.formfield(
                self,
                form_class=core_fields.CremeUserEnumerableField,
                model=self.model,
                field_name=self.name,
                required=not self.blank,
                empty_label=_('No user') if self.blank else _('Select a user…'),
                **kwargs
            )
        else:
            # This case is probably meaningless...
            super().formfield(
                **{'form_class': forms.CharField, **kwargs}
            )

    def get_internal_type(self):
        return 'ForeignKey'


# NB: using <descriptor_class> is harder than just move __get__/__set__ in a
#     class for CTypeForeignKey & CTypeOneToOneField...
class CTypeDescriptorMixin:
    def __get__(self, instance, instance_type=None):
        ct_id = getattr(instance, self.attname)
        return ContentType.objects.get_for_id(ct_id) if ct_id else None

    def __set__(self, instance, value):
        if not value:
            ct_id = None
        elif isinstance(value, ContentType):
            ct_id = value.id
        else:
            ct_id = ContentType.objects.get_for_model(value).id

        setattr(instance, self.attname, ct_id)


class CTypeForeignKey(CTypeDescriptorMixin, models.ForeignKey):
    def __init__(self, **kwargs):
        kwargs['to'] = 'contenttypes.ContentType'
        # In a normal use, ContentType instances are never deleted ;
        # so CASCADE by default should be OK
        kwargs.setdefault('on_delete', CASCADE)
        super().__init__(**kwargs)

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

        # BEWARE: we don't call super(CTypeForeignKey, self).formfield(**defaults)
        # to avoid useless/annoying 'queryset' arg
        return super(models.ForeignKey, self).formfield(
            **{'form_class': CTypeChoiceField, **kwargs}
        )


class EntityCTypeForeignKey(CTypeForeignKey):
    # TODO: assert that it is a CremeEntity instance ??
    # def __set__(self, instance, value):
    #     setattr(instance, self.attname, value.id if value else value)

    def formfield(self, **kwargs):
        from ..forms.fields import EntityCTypeChoiceField

        return super().formfield(**{'form_class': EntityCTypeChoiceField, **kwargs})


class CTypeOneToOneField(CTypeDescriptorMixin, models.OneToOneField):
    def __init__(self, **kwargs):
        kwargs['to'] = 'contenttypes.ContentType'

        # In a normal use, ContentType instances are never deleted ;
        # so CASCADE by default should be OK
        kwargs.setdefault('on_delete', CASCADE)
        if kwargs.get('primary_key'):
            kwargs['parent_link'] = True

        super().__init__(**kwargs)

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

        # BEWARE: we don't call super(CTypeOneToOneField, self).formfield(**defaults)
        # to avoid useless/annoying 'queryset' arg
        return super(models.OneToOneField, self).formfield(
            **{'form_class': CTypeChoiceField, **kwargs}
        )


# NB: based on <django.contrib.contenttypes.fields.GenericForeignKey>
class RealEntityForeignKey(FieldCacheMixin):
    """ Provide a "virtual" field which uses & combines 2 ForeignKeys :
     - a ForeignKey to CremeEntity.
     - a ForeignKey to ContentType (tips: it works well with a EntityCTypeForeignKey).

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

    def __str__(self):
        meta = self.model._meta

        return f'{meta.app_label}.{meta.object_name}.{self.name}'

    def contribute_to_class(self, cls, name, **kwargs):
        self.name = name
        self.model = cls
        cls._meta.add_field(self, private=True)
        setattr(cls, name, self)

    def check(self, **kwargs):
        from .entity import CremeEntity

        return [
            *self._check_field_name(),
            *self._check_fk('_ct_field_name', ContentType),
            *self._check_fk('_fk_field_name', CremeEntity)
        ]

    def _check_field_name(self):
        if self.name.endswith('_'):
            yield checks.Error(
                'Field names must not end with an underscore.',
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
                f'The RealEntityForeignKey references the non-existent field "{fname}".',
                obj=self,
                id='creme.E008',
            )
        else:
            if not isinstance(field, models.ForeignKey):
                yield checks.Error(
                    f'"{meta.object_name}.{fname}" is not a ForeignKey.',
                    obj=self,
                    id='creme.E008',
                )
            elif field.remote_field.model != related_model:
                rel_meta = related_model._meta

                yield checks.Error(
                    f'"{meta.object_name}.{fname}" is not a ForeignKey to '
                    f'"{rel_meta.app_label}.{rel_meta.object_name}".',
                    obj=self,
                    id='creme.E008',
                )

    @staticmethod
    def _ctype_or_die(ct):
        if ct is None:
            raise ValueError(
                'The content type is not set while the entity is. '
                'HINT: set both by hand or just use the RealEntityForeignKey setter.'
            )

    def __get__(self, instance, cls=None):
        # NB: when reading the attribute from the class (ex: prefetch_related()).
        if instance is None:
            return self

        real_entity = self.get_cached_value(instance, default=None)

        if real_entity is None:
            get_field = self.model._meta.get_field

            # NB:  <ct = getattr(instance, self._ct_field_name)> will perform an additional
            # query if the field is not a (Entity)CTypeForeignKey instance.  TODO: unit test
            ct_field = get_field(self._ct_field_name)
            ct_id = getattr(instance, ct_field.get_attname())
            ct = ContentType.objects.get_for_id(ct_id) if ct_id else None

            fk_field = get_field(self._fk_field_name)

            try:
                entity = fk_field.get_cached_value(instance)
            except KeyError:
                entity_id = getattr(instance, fk_field.get_attname())

                if entity_id is None:
                    real_entity = None
                else:
                    self._ctype_or_die(ct)

                    real_entity = ct.model_class()._default_manager.get(id=entity_id)

                setattr(instance, self._fk_field_name, real_entity)
            else:
                if entity is None:
                    real_entity = None
                else:
                    self._ctype_or_die(ct)

                    if entity.entity_type_id != ct.id:
                        raise ValueError('The content type does not match this entity.')

                    real_entity = entity.get_real_entity()

            self.set_cached_value(instance, real_entity)

        return real_entity

    def __set__(self, instance, value):
        ct = None

        if value is not None:
            ct = value.entity_type
            real_entity = value._real_entity

            # NB: if the entity is not real & the real entity has not been
            #     retrieved yet, we do not cache it to retrieve it lazily in __get__
            if real_entity is not None:
                self.set_cached_value(
                    instance,
                    value if real_entity is True else real_entity,
                )
        else:
            self.set_cached_value(instance, value)

        setattr(instance, self._ct_field_name, ct)
        setattr(instance, self._fk_field_name, value)

    @property
    def cache_name(self):  # See FieldCacheMixin
        return self.name

    def get_prefetch_querysets(self, instances, querysets=None):
        if querysets is not None:
            raise ValueError("Custom queryset can't be used for this lookup.")

        # For efficiency, group the instances by content type and then do 1 query per model
        fk_dict = defaultdict(set)

        # We need one instance for each group in order to get the right db
        instance_dict = {}

        get_field = self.model._meta.get_field
        ct_attname = get_field(self._ct_field_name).get_attname()
        fk_field = get_field(self._fk_field_name).get_attname()

        for instance in instances:
            # We avoid looking for values if either ct_id or fkey value is None
            ct_id = getattr(instance, ct_attname)
            if ct_id is not None:
                entity_id = getattr(instance, fk_field)
                if entity_id is not None:
                    fk_dict[ct_id].add(entity_id)
                    instance_dict[ct_id] = instance

        entities = []
        for ct_id, fkeys in fk_dict.items():
            instance = instance_dict[ct_id]
            ct = ContentType.objects.db_manager(instance._state.db).get_for_id(ct_id)
            entities.extend(ct.get_all_objects_for_this_type(pk__in=fkeys))

        return (
            entities,
            lambda entity: entity.pk,
            lambda obj: getattr(obj, fk_field),
            True,  # single
            self.name,  # cache name
            True,  # is descriptor (can use setattr())
        )


class BasicAutoField(models.PositiveIntegerField):
    """BasicAutoField is a PositiveIntegerField which uses an auto-incremented
    value when no value is given.

    Notice that the method is really simple, so the limits are :
        - The value is the maximum value plus one, so it does not remember the
          deleted maximum values.
        - There could be a race condition on the maximum computing.

    This field is OK for 'order' in ordered model as creme_config wants them because:
        - creme_config fixes the order problems (duplication, 'hole').
        - order are principally use by GUI, and are not a business constraint.
    """
    def __init__(self, *args, **kwargs):
        setdefault = kwargs.setdefault
        setdefault('editable', False)
        setdefault('blank',    True)

        # Not '1', in order to distinguish an initialised value from a non initialised one.
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
#  Copyright (C) 2009-2025  Hybird
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

class CreationDateTimeField(models.DateTimeField):
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
