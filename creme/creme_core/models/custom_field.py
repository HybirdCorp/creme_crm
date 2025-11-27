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

from __future__ import annotations

from collections import OrderedDict, defaultdict
from collections.abc import Iterable, Sequence
from typing import Any, DefaultDict
from uuid import uuid4

from django import forms
from django.core.validators import EMPTY_VALUES
from django.db import models
from django.utils.formats import date_format, number_format
from django.utils.timezone import localtime
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from ..global_info import get_per_request_cache
from ..utils.content_type import as_ctype
from .base import CremeModel
from .entity import CremeEntity
from .fields import CremeURLField, CTypeForeignKey

__all__ = (
    'CustomField', 'CustomFieldValue',
    'CustomFieldInteger', 'CustomFieldFloat', 'CustomFieldBoolean',
    'CustomFieldString', 'CustomFieldText', 'CustomFieldURL',
    'CustomFieldDateTime', 'CustomFieldDate',
    'CustomFieldEnumValue', 'CustomFieldEnum', 'CustomFieldMultiEnum',
)


class CustomFieldManager(models.Manager):
    # TODO: exclude deleted fields?
    def compatible(self, ct_or_model, /):
        return self.filter(content_type=as_ctype(ct_or_model))

    # TODO: use UUIDs as keys instead of IDs?
    # TODO: exclude deleted fields?
    def get_for_model(self, ct_or_model, /) -> dict[int, CustomField]:
        ct = as_ctype(ct_or_model)
        cache = get_per_request_cache()
        key = f'creme_core-custom_fields-{ct.id}'

        cached_cfields = cache.get(key)
        if cached_cfields is None:
            cached_cfields = cache[key] = [*self.filter(content_type=ct)]

        return OrderedDict((cfield.id, cfield) for cfield in cached_cfields)


class CustomField(CremeModel):
    # TODO: use an enum.IntEnum ? (see creme_core.gui.listview.search.CustomFieldSearchRegistry)
    INT         = 1
    FLOAT       = 2
    BOOL        = 3
    STR         = 10
    TEXT        = 11
    URL         = 12
    DATETIME    = 20
    DATE        = 21
    ENUM        = 100
    MULTI_ENUM  = 101

    uuid = models.UUIDField(unique=True, editable=False, default=uuid4)
    name = models.CharField(_('Field name'), max_length=100)
    content_type = CTypeForeignKey(verbose_name=_('Related type'))
    field_type = models.PositiveSmallIntegerField(_('Field type'))  # See INT, FLOAT etc...
    is_required = models.BooleanField(
        _('Is required?'), default=False,
        help_text=_(
            'A required custom-field must be filled when a new entity is created; '
            'existing entities are not immediately impacted.'
        ),
    )
    is_deleted = models.BooleanField(_('Is deleted?'), default=False, editable=False)
    description = models.TextField(
        _('Description'), blank=True,
        help_text=_('The description is notably used in forms to help user'),
    )
    # default_value = CharField(_('Default value'), max_length=100, blank=True, null=True)
    # extra_args    = CharField(max_length=500, blank=True, null=True)

    objects = CustomFieldManager()

    creation_label = _('Create a custom field')
    save_label     = _('Save the custom field')

    class Meta:
        app_label = 'creme_core'
        verbose_name = _('Custom field')
        verbose_name_plural = _('Custom fields')
        unique_together = ('content_type', 'name')
        ordering = ('id',)

    def __str__(self):
        return self.name

    def delete(self, *args, **kwargs):
        for value_class in _TABLES.values():
            value_class.objects.filter(custom_field=self).delete()

        # Beware: we don't call the CustomFieldEnumValue.delete() to avoid loop.
        self.customfieldenumvalue_set.all().delete()

        super().delete(*args, **kwargs)

    @property
    def value_class(self) -> type[CustomFieldValue]:
        return _TABLES[self.field_type]

    def get_formfield(self, custom_value, user=None):
        return self.value_class.get_formfield(self, custom_value, user=user)

    @staticmethod
    def get_custom_values_map(entities: Iterable[CremeEntity],
                              custom_fields: Iterable[CustomField],
                              ) -> DefaultDict[int, dict[int, Any]]:
        """
        @return { Entity's id -> { CustomField's id -> CustomValue } }
        """
        cfield_map = defaultdict(list)
        for cfield in custom_fields:
            cfield_map[cfield.field_type].append(cfield)

        cvalues_map: DefaultDict[int, dict[int, Any]] = defaultdict(dict)
        # NB: 'list(entities)' ==> made strangely a query for every entity ;(
        entities = [e.id for e in entities]

        for field_type, cfields_list in cfield_map.items():
            for cvalue in _TABLES[field_type]._get_4_entities(entities, cfields_list):
                cvalues_map[cvalue.entity_id][cvalue.custom_field_id] = cvalue

        return cvalues_map


class CustomFieldValue(CremeModel):
    custom_field = models.ForeignKey(CustomField, on_delete=models.CASCADE)
    entity = models.ForeignKey(CremeEntity, on_delete=models.CASCADE)
    # value       = FoobarField()  --> implement in inherited classes

    class Meta:
        abstract = True

    def __str__(self):
        return str(self.value)

    @classmethod
    def _get_4_entities(cls, entities, cfields):
        """Retrieve all custom values for a list of custom fields with the same type.
        Trick: override me to optimise the query (e.g. use a select_related())
        """
        return cls.objects.filter(custom_field__in=cfields, entity__in=entities)

    @classmethod
    def get_related_name(cls):
        return cls.__name__.lower()

    @staticmethod
    def _build_formfield(custom_field: CustomField,
                         formfield: forms.Field,
                         user=None,
                         ) -> None:
        pass

    def _set_formfield_value(self, field: forms.Field) -> None:
        field.initial = self.value

    @staticmethod
    def _get_formfield(**kwargs) -> forms.Field:
        raise NotImplementedError

    @classmethod
    def get_formfield(cls,
                      custom_field: CustomField,
                      custom_value,
                      user=None,
                      ) -> forms.Field:
        field = cls._get_formfield(
            label=custom_field.name,
            required=custom_field.is_required,
            help_text=custom_field.description,
        )
        cls._build_formfield(custom_field, field, user)
        if custom_value:
            custom_value._set_formfield_value(field)

        return field

    def set_value_n_save(self, value) -> None:
        if self.value != value:
            self.value = value
            self.save()

    @staticmethod
    def is_empty_value(value) -> bool:
        return value in EMPTY_VALUES

    @classmethod
    def save_values_for_entities(cls,
                                 custom_field: CustomField,
                                 entities: Sequence[CremeEntity],
                                 value,
                                 ) -> None:
        cfv_klass = custom_field.value_class

        cf_values_qs = cfv_klass.objects.filter(
            custom_field=custom_field,
            entity__in=entities,
        )

        if cls.is_empty_value(value):
            cf_values_qs.delete()
            for entity in entities:
                entity._cvalues_map[custom_field.id] = None
        else:
            cf_values = {
                cf_value.entity_id: cf_value
                for cf_value in cf_values_qs
            }

            for entity in entities:
                try:
                    custom_value = cf_values[entity.id]
                except KeyError:
                    custom_value = cfv_klass(custom_field=custom_field, entity=entity)

                custom_value.set_value_n_save(value)
                entity._cvalues_map[custom_field.id] = custom_value


class CustomFieldString(CustomFieldValue):
    value = models.CharField(max_length=100)

    verbose_name = _('Short string')

    class Meta:
        app_label = 'creme_core'

    def __str__(self):
        return self.value

    @staticmethod
    def _get_formfield(**kwargs):
        return forms.CharField(**kwargs)


class CustomFieldText(CustomFieldValue):
    value = models.TextField()

    verbose_name = _('Long text')

    class Meta:
        app_label = 'creme_core'

    @staticmethod
    def _get_formfield(**kwargs):
        return forms.CharField(
            widget=forms.Textarea,
            **kwargs
        )


class CustomFieldURL(CustomFieldValue):
    # value = models.URLField()
    value = CremeURLField(max_length=200)

    verbose_name = _('URL (link)')

    class Meta:
        app_label = 'creme_core'

    # TODO: make <@classmethod> & retrieve 200 in field/attribute
    @staticmethod
    def _get_formfield(**kwargs):
        return forms.CharField(max_length=200, **kwargs)


class CustomFieldInteger(CustomFieldValue):
    value = models.IntegerField()

    verbose_name = _('Integer')

    class Meta:
        app_label = 'creme_core'

    @staticmethod
    def _get_formfield(**kwargs):
        return forms.IntegerField(**kwargs)


# TODO: rename CustomFieldDecimal
class CustomFieldFloat(CustomFieldValue):
    _MAX_DIGITS = 12
    _DECIMAL_PLACES = 2

    value = models.DecimalField(max_digits=_MAX_DIGITS, decimal_places=_DECIMAL_PLACES)

    verbose_name = _('Decimal')

    class Meta:
        app_label = 'creme_core'

    # TODO: factorise with gui.field_printers
    def __str__(self):
        value = self.value
        return number_format(value) if value else ''

    @staticmethod
    def _get_formfield(**kwargs):
        return forms.DecimalField(
            max_digits=CustomFieldFloat._MAX_DIGITS,
            decimal_places=CustomFieldFloat._DECIMAL_PLACES,
            **kwargs
        )


class CustomFieldDateTime(CustomFieldValue):
    value = models.DateTimeField()

    verbose_name = _('Date and time')

    class Meta:
        app_label = 'creme_core'

    def __str__(self):
        value = self.value
        return date_format(localtime(value), 'DATETIME_FORMAT') if value else ''

    @staticmethod
    def _get_formfield(**kwargs):
        return forms.DateTimeField(**kwargs)


class CustomFieldDate(CustomFieldValue):
    value = models.DateField()

    verbose_name = _('Date')

    class Meta:
        app_label = 'creme_core'

    @staticmethod
    def _get_formfield(**kwargs):
        return forms.DateField(**kwargs)

    def __str__(self):
        value = self.value
        return date_format(value, 'DATE_FORMAT') if value else ''


class CustomFieldBoolean(CustomFieldValue):
    value = models.BooleanField(default=False)

    verbose_name = _('Boolean (2 values: Yes/No)')

    class Meta:
        app_label = 'creme_core'

    def __str__(self):
        return gettext('Yes') if self.value else gettext('No')

    @staticmethod
    def _get_formfield(**kwargs):
        required = kwargs.get('required', False)
        kwargs['required'] = False

        return (
            forms.BooleanField(**kwargs)
            if required else
            forms.NullBooleanField(**kwargs)
        )

    def set_value_n_save(self, value):
        # Boolean default value is False
        if value is not None:
            self.value = value
            self.save()


class CustomFieldEnumValue(CremeModel):
    custom_field = models.ForeignKey(
        CustomField, related_name='customfieldenumvalue_set', on_delete=models.CASCADE,
    )
    value = models.CharField(max_length=100)
    uuid = models.UUIDField(
        unique=True, editable=False, default=uuid4,
    ).set_tags(viewable=False)

    class Meta:
        app_label = 'creme_core'

    def __str__(self):
        return self.value

    def delete(self, *args, **kwargs):
        CustomFieldEnum.objects.filter(
            custom_field=self.custom_field_id, value=str(self.id),
        ).delete()
        super().delete(*args, **kwargs)


class CustomFieldEnum(CustomFieldValue):
    value = models.ForeignKey(CustomFieldEnumValue, on_delete=models.CASCADE)

    verbose_name = _('Choice list')

    class Meta:
        app_label = 'creme_core'

    @staticmethod
    def _get_formfield(**kwargs):
        from creme.creme_config.forms.fields import (
            CreatorCustomEnumerableChoiceField,
        )

        return CreatorCustomEnumerableChoiceField(**kwargs)

    @classmethod
    def _get_4_entities(cls, entities, cfields):
        return cls.objects.filter(custom_field__in=cfields, entity__in=entities) \
                          .select_related('value')

    @staticmethod
    def _build_formfield(custom_field, formfield, user=None):
        formfield.user = user
        formfield.custom_field = custom_field

    def _set_formfield_value(self, field):
        field.initial = self.value_id

    def set_value_n_save(self, value):
        value_id = int(value)
        if self.value_id != value_id:
            self.value_id = value_id
            self.save()


class CustomFieldMultiEnum(CustomFieldValue):
    value = models.ManyToManyField(CustomFieldEnumValue)

    verbose_name = _('Multiple choice list')

    class Meta:
        app_label = 'creme_core'

    def __str__(self):
        return ' / '.join(str(val) for val in self.get_enumvalues())

    @staticmethod
    def _get_formfield(**kwargs):
        from creme.creme_config.forms.fields import CustomMultiEnumChoiceField

        return CustomMultiEnumChoiceField(**kwargs)

    @classmethod
    def _get_4_entities(cls, entities, cfields):
        # TODO: for a m2m select_related() doesn't work
        #       -> can fill the enumvalues cache easily (must use BaseQuery.join in query.py ....)
        return cls.objects.filter(custom_field__in=cfields, entity__in=entities)

    @staticmethod
    def _build_formfield(custom_field, formfield, user=None):
        formfield.choices = CustomFieldEnumValue.objects\
                                                .filter(custom_field=custom_field) \
                                                .values_list('id', 'value')
        formfield.user = user
        formfield.custom_field = custom_field

    def get_enumvalues(self) -> list[CustomFieldValue]:
        return self.get_m2m_values('value')

    def _set_formfield_value(self, field):
        field.initial = self.value.all().values_list('id', flat=True)

    def set_value_n_save(self, value):
        if not self.pk:
            self.save()  # M2M field need a pk

        self.value.set(value)


_TABLES: dict[int, type[CustomFieldValue]] = OrderedDict([
    (CustomField.INT,        CustomFieldInteger),
    (CustomField.FLOAT,      CustomFieldFloat),
    (CustomField.BOOL,       CustomFieldBoolean),
    (CustomField.STR,        CustomFieldString),
    (CustomField.TEXT,       CustomFieldText),
    (CustomField.URL,        CustomFieldURL),
    (CustomField.DATE,       CustomFieldDate),
    (CustomField.DATETIME,   CustomFieldDateTime),
    (CustomField.ENUM,       CustomFieldEnum),
    (CustomField.MULTI_ENUM, CustomFieldMultiEnum),
])
