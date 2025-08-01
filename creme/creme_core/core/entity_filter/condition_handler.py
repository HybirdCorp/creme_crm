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

import logging
from datetime import datetime
from decimal import Decimal
from functools import partial
from typing import Literal
from uuid import UUID

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db.models import (
    BooleanField,
    ForeignKey,
    ManyToManyField,
    Model,
    Q,
)
from django.utils.formats import date_format
from django.utils.hashable import make_hashable
from django.utils.timezone import make_aware, now
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

import creme.creme_core.forms.entity_filter.fields as ef_fields
from creme.creme_core.models import (
    CremeEntity,
    CremeProperty,
    CremePropertyType,
    CustomField,
    CustomFieldEnumValue,
    EntityFilter,
    EntityFilterCondition,
    Relation,
    RelationType,
)
from creme.creme_core.models.custom_field import _TABLES
from creme.creme_core.models.utils import model_verbose_name_plural
from creme.creme_core.utils.date_range import date_range_registry
from creme.creme_core.utils.dates import date_2_dict
from creme.creme_core.utils.meta import FieldInfo, is_date_field

from ..field_tags import FieldTag
from . import (
    EF_REGULAR,
    EntityFilterRegistry,
    entity_filter_registries,
    operands,
    operators,
)

logger = logging.getLogger(__name__)


class FilterConditionHandler:
    """A condition handler is linked to an instance of
    <creme_core.models.EntityFilterCondition> & provide the behaviour specific
    to the condition type.

    The main feature is provided by the method 'get_q()' ; generating a
    <django.models.Q> object to filter entities by one of their model-field or
    by the presence of a CremeProperty are different behaviours of course.
    These behaviours are implemented in child-classes.

    All child-classes are registered in an instance of
    <creme_core.core.entity_filter._EntityFilterRegistry>.
    """
    type_id: int

    class DataError(Exception):
        pass

    class ValueError(Exception):
        pass

    _model: type[CremeEntity]
    _subfilter: EntityFilter | None | bool

    def __init__(self, *, efilter_type: str, model: type[CremeEntity]):
        """Constructor.

        @param efilter_type: See <creme_core.models.EntityFilter.filter_type>.
        @param model: class inheriting <creme_core.models.CremeEntity>.
        """
        self._efilter_type = efilter_type
        self._model = model

        # 'None' means not retrieved ; 'False' means invalid filter
        self._subfilter = None

    @property
    def efilter_type(self):
        return self._efilter_type

    @property
    def efilter_registry(self):
        # TODO: in __init__ for early error?
        return entity_filter_registries[self._efilter_type]

    def accept(self, *, entity: CremeEntity, user) -> bool:
        """Check if a CremeEntity instance is accepted or refused by the handler.

        @param entity: Instance of <CremeEntity>.
        @param user: Instance of <django.contrib.auth.get_user_model()> ; it's
               the current user (it is used to retrieve it & its teams by the
               operand <CurrentUserOperand>).
        @return: A boolean; <True> means the entity is accepted.
        """
        raise NotImplementedError

    @property
    def applicable_on_entity_base(self) -> bool:
        """Can this handler be applied on CremeEntity (QuerySet or simple instance)?
        E.g. if the handler reads a model-field specific to a child class, it
            won't be applicable to CremeEntity.
        """
        return False

    @classmethod
    def build(cls, *,
              efilter_type: str,
              model: type[CremeEntity],
              name: str,
              data: dict | None,
              ) -> FilterConditionHandler:
        "Get an instance of FilterConditionHandler from serialized data."
        raise NotImplementedError

    def description(self, user):
        "Human-readable string explaining the handler."
        raise NotImplementedError

    def entities_are_distinct(self) -> bool:
        return True

    @property
    def error(self) -> str | None:
        """Get error corresponding to invalid data contained in the condition.
        @return: A string if there is an error, or None.
        """
        return None

    @classmethod
    def formfield(cls, form_class=None, **kwargs):
        raise NotImplementedError

    def get_q(self, user) -> Q:
        """Get the query which filter the entities with the expected behaviour.

        @param user: <django.contrib.auth.get_user_model()> instance ;
               used to check credentials.
        @return: An instance of <django.models.Q>.
        """
        raise NotImplementedError

    @property
    def model(self) -> type[CremeEntity]:
        return self._model

    @classmethod
    def query_for_related_conditions(cls, instance: Model) -> Q:
        """Get a Q instance to retrieve EntityFilterConditions which are
        related to an instance.
        It's useful to delete useless conditions (their related instance is deleted).
        """
        return Q()

    @classmethod
    def query_for_parent_conditions(cls, ctype: ContentType) -> Q:
        """Get a Q instance to retrieve EntityFilterConditions which have
        potentially sub-filters for a given ContentType.
        It's useful to build EntityFilters tree (to check cycle etc...).
        """
        return Q()

    @property
    def subfilter(self) -> EntityFilter | bool:
        "@return: An EntityFilter instance or 'False' is there is no valid sub-filter."
        subfilter = self._subfilter

        if subfilter is None:
            sf_id = self.subfilter_id

            if sf_id is None:
                subfilter = False
            else:
                subfilter = EntityFilter.objects.filter(id=self.subfilter_id).first() or False

            self._subfilter = subfilter

        return subfilter

    @property
    def subfilter_id(self) -> str | None:
        "@return: An ID of an EntityFilter, or None."
        return None


class SubFilterConditionHandler(FilterConditionHandler):
    """Filter entities with a (sub) EntityFilter."""
    type_id = 1

    DESCRIPTION_FORMAT = _('Entities are accepted by the filter «{}»')

    def __init__(self, *,
                 efilter_type: str,
                 model: type[CremeEntity] | None = None,
                 subfilter: EntityFilter | str,
                 ):
        """Constructor.

        @param model: Class inheriting <creme_core.models.CremeEntity>
               (ignored if an EntityFilter instance is passed for "subfilter" -- see below).
        @param subfilter: <creme_core.models.EntityFilter> instance or ID (string).
        """
        if isinstance(subfilter, EntityFilter):
            super().__init__(
                efilter_type=efilter_type,
                model=subfilter.entity_type.model_class(),
            )
            self._subfilter_id = subfilter.id
            self._subfilter    = subfilter  # TODO: copy ?
        else:
            if model is None:
                raise TypeError(
                    'The argument "model" must be passed if a filter ID is passed.'
                )

            super().__init__(efilter_type=efilter_type, model=model)
            self._subfilter_id = subfilter

    def accept(self, *, entity, user):
        return self.subfilter.accept(entity=entity, user=user)

    @property
    def applicable_on_entity_base(self):
        return self.subfilter.applicable_on_entity_base

    @classmethod
    def build(cls, *, efilter_type, model, name, data):
        return cls(efilter_type=efilter_type, model=model, subfilter=name)

    @classmethod
    def build_condition(cls,
                        subfilter: EntityFilter,
                        filter_type: str = EF_REGULAR,  # TODO: rename "efilter_type"...
                        condition_cls=EntityFilterCondition,
                        ):
        """Build an (unsaved) EntityFilterCondition.

        @param subfilter: <creme_core.models.EntityFilter> instance.
        @param filter_type: see the field 'EntityFilter.filter_type'.
        @param condition_cls: Class of condition.
        """
        assert isinstance(subfilter, EntityFilter)

        return condition_cls(
            filter_type=filter_type,
            type=cls.type_id,
            model=subfilter.entity_type.model_class(),
            name=subfilter.id,
            # NB: avoid a query to retrieve again the sub-filter (in forms).
            # TODO: assert this class is available in the registry ?
            handler=cls(efilter_type=filter_type, subfilter=subfilter),
        )

    def description(self, user):
        subfilter = self.subfilter

        return self.DESCRIPTION_FORMAT.format(subfilter) if subfilter else '???'

    def entities_are_distinct(self):
        return self.subfilter.entities_are_distinct

    @property
    def error(self):
        if self.subfilter is False:
            return f"'{self.subfilter_id}' is not a valid filter ID"

    @classmethod
    def formfield(cls, form_class=ef_fields.SubfiltersConditionsField, **kwargs):
        defaults = {'label': _('Sub-filters'), **kwargs}

        return form_class(**defaults)

    def get_q(self, user):
        return self.subfilter.get_q(user)

    @classmethod
    def query_for_parent_conditions(cls, ctype):
        return Q(
            type=cls.type_id,
            filter__entity_type=ctype,
        )

    @property
    def subfilter_id(self):
        return self._subfilter_id


class OperatorConditionHandlerMixin:
    efilter_registry: EntityFilterRegistry

    def _check_operator(self, operator_id):
        if self.get_operator(operator_id) is None:
            return f"Operator ID '{operator_id}' is invalid"

    def get_operand(self, value, user) -> operands.ConditionDynamicOperand | None:
        return self.efilter_registry.get_operand(type_id=value, user=user)

    def get_operator(self, operator_id: int) -> operators.ConditionOperator | None:
        return self.efilter_registry.get_operator(operator_id)

    def resolve_operands(self, values, user):
        """Return a list where:
            - values which does not correspond to a special dynamic operand are unchanged.
            - values corresponding to a special dynamic operand are resoled with this one.
        """
        resolved_values = []

        for value in values:
            operand = self.get_operand(value=value, user=user)
            if operand is None:
                resolved_values.append(value)
            else:
                resolved_value = operand.resolve()
                if isinstance(resolved_value, list):
                    resolved_values.extend(resolved_value)
                else:
                    resolved_values.append(resolved_value)

        return resolved_values


class BaseRegularFieldConditionHandler(FilterConditionHandler):
    def __init__(self, *, model, efilter_type, field_name: str):
        super().__init__(model=model, efilter_type=efilter_type)
        self._field_name: str = field_name

    @property
    def applicable_on_entity_base(self):
        return self.field_info[0] in CremeEntity._meta.fields

    @property
    def field_info(self) -> FieldInfo:
        return FieldInfo(self._model, self._field_name)  # TODO: cache ?


class RegularFieldConditionHandler(OperatorConditionHandlerMixin,
                                   BaseRegularFieldConditionHandler):
    """Filter entities by using one of their fields.
    Note: no date field; see <DateRegularFieldConditionHandler>.
    """
    type_id = 5

    def __init__(self, *, model, efilter_type, field_name, operator_id, values) -> None:
        super().__init__(
            model=model, efilter_type=efilter_type, field_name=field_name,
        )
        self._operator_id: int = operator_id
        self._values = values
        self._verbose_values = None  # Cache for values in description()

    @property
    def operator_id(self):
        return self._operator_id

    def accept(self, *, entity, user):
        operator = self.get_operator(self._operator_id)
        values = self.resolve_operands(values=self._values, user=user)

        field_info = self.field_info
        last_field = field_info[-1]

        if isinstance(last_field, ForeignKey):
            # NB: we want to retrieve ID & not instance (we store ID in 'values'
            #     & want to avoid some queries).
            base_instance = (
                entity
                if len(field_info) == 1 else
                field_info[:-1].value_from(entity)
            )
            field_value = (
                None
                if base_instance is None else
                getattr(base_instance, field_info[-1].attname)
            )

            # TODO: move this test in operator code + factorise ?
            if not isinstance(operator, operators.IsEmptyOperator):
                values = [*map(last_field.to_python, values)]
        elif isinstance(last_field, ManyToManyField):
            # NB: see ForeignKey remark
            base_instance = (
                entity
                if len(field_info) == 1 else
                field_info[:-1].value_from(entity)
            )
            # NB: <or None> to send at least one value (useful for "is empty" operator
            field_value = (
                None
                if base_instance is None else
                # NB: see remark about Snapshot in get_m2m_values()'s docstring
                [o.pk for o in base_instance.get_m2m_values(last_field.attname)] or None
            )

            # TODO: move this test in operator code...
            # TODO: test (need M2M with str PK)
            if not isinstance(operator, operators.IsEmptyOperator):
                values = [*map(last_field.target_field.to_python, values)]
        else:
            # HACK: string format (would be better to convert data before)
            # TODO: move this test in operator code...
            if not isinstance(operator, operators.IsEmptyOperator):
                values = [*map(last_field.to_python, values)]

            field_value = field_info.value_from(entity)

        accept = partial(operator.accept, values=values)

        return (
            any(accept(field_value=i) for i in field_value)
            if isinstance(field_value, list) else
            accept(field_value=field_value)
        )

    # TODO: multi-value is stupid for some operator (LT, GT etc...) => improve checking ???
    @classmethod
    def build(cls, *, efilter_type, model, name, data):
        try:
            kwargs = {
                'operator_id': int(data['operator']),
                'values':      data['values'],
            }
        except (TypeError, KeyError, ValueError) as e:
            raise cls.DataError(
                f'{cls.__name__}.build(): invalid data ({e})'
            )

        return cls(efilter_type=efilter_type, model=model, field_name=name, **kwargs)

    @classmethod
    def build_condition(cls, *, model, field_name, operator, values,
                        user=None,
                        filter_type=EF_REGULAR,
                        condition_cls=EntityFilterCondition,
                        ):
        """Build an (unsaved) EntityFilterCondition.

        @param model: Class inheriting <creme_core.models.CremeEntity>.
        @param field_name: Name of the field.
        @param operator: <creme_core.core.entity_filter.operators.ConditionOperator> ID or class.
        @param values: List of searched values (logical OR between them).
               Exceptions: - RANGE: 'values' is always a list of 2 elements
                           - ISEMPTY: 'values' is a list containing one boolean.
        @param user: Some fields need a user instance for permission validation.
        @param filter_type: see the field 'EntityFilter.filter_type'.
        @param condition_cls: Class of condition.
        """
        operator_id = operator if isinstance(operator, int) else operator.type_id

        registry = entity_filter_registries[filter_type]
        operator_obj = registry.get_operator(operator_id)
        if operator_obj is None:
            raise cls.ValueError(
                f'{cls.__name__}.build_condition(): unknown operator ID="{operator_id}"'
            )

        try:
            finfo = FieldInfo(model, field_name)
        except FieldDoesNotExist as e:
            raise cls.ValueError(str(e)) from e

        field = finfo[-1]

        try:
            # TODO: cast more values (e.g. integers instead of "digit" string)
            values = operator_obj.validate_field_values(
                field=field, values=values, user=user,
                efilter_registry=registry,
            )
        except ValidationError as e:
            raise cls.ValueError(
                gettext('Condition on field «{field}»: {error}').format(
                    field=field.verbose_name,
                    error='\n'.join(e.messages),
                )
            ) from e
        except Exception as e:
            raise cls.ValueError(str(e)) from e

        return condition_cls(
            filter_type=filter_type,
            model=model,
            type=cls.type_id,
            name=field_name,
            value={'operator': operator_obj.type_id, 'values': values},
        )

    def description(self, user):
        finfo = self.field_info
        values = self._verbose_values
        operator = self.get_operator(self._operator_id)

        if values is None:
            last_field = finfo[-1]

            if (
                isinstance(last_field, ForeignKey | ManyToManyField)
                # TODO: meh; need a better API in operators
                and not isinstance(operator, operators.BooleanOperatorBase)
            ):
                values = []
                pks = []

                for value in self._values:
                    operand = self.get_operand(value=value, user=user)

                    if operand:
                        values.append(operand.verbose_name)
                    else:
                        pks.append(value)

                # NB: invalid ID are ignored (deleted instances do not cause
                #     the deletion of condition yet, like with Relation/CremeProperty).
                related_model = last_field.remote_field.model

                try:
                    instances = [*related_model._default_manager.filter(pk__in=pks)]
                except ValueError:
                    logger.exception(
                        'Error in %s.description() while retrieving instance of %s with ID=%s',
                        type(self).__name__, related_model, self._values,
                    )
                    values.append('???')
                else:
                    values.extend(
                        instance.allowed_str(user)
                        if hasattr(instance, 'allowed_str') else
                        instance
                        for instance in instances
                    )
            elif last_field.choices:
                # See Model._get_FIELD_display()
                get_choice = dict(make_hashable(last_field.flatchoices)).get
                values = [
                    get_choice(make_hashable(value), value) for value in self._values
                ]
            # TODO: add an extensible system to render verbose values?
            # TODO: IntegerField etc...?
            elif isinstance(last_field, BooleanField):
                values = [_('True') if value else _('False') for value in self._values]
            else:
                # TODO: operand too...
                # TODO: copy to be consistent with other cases?
                values = self._values

            self._verbose_values = values

        return operator.description(
            field_vname=finfo.verbose_name,
            values=values,
        )

    def entities_are_distinct(self):
        return not isinstance(self.field_info[0], ManyToManyField)

    @property
    def error(self):
        try:
            field_info = self.field_info
        except FieldDoesNotExist as e:
            return str(e)

        if not all(field.get_tag(FieldTag.VIEWABLE) for field in field_info):
            return f'{self._model.__name__}.{self._field_name} is not viewable'

        return self._check_operator(self._operator_id)

    @classmethod
    def formfield(cls, form_class=ef_fields.RegularFieldsConditionsField, **kwargs):
        defaults = {
            'label': _('On regular fields'),
            'help_text': _('You can write several values, separated by commas.'),
            **kwargs
        }

        return form_class(**defaults)

    def get_q(self, user):
        operator = self.get_operator(self._operator_id)
        values = self.resolve_operands(values=self._values, user=user)
        field_info = self.field_info

        # HACK: old format compatibility for boolean fields.
        last_field = field_info[-1]
        if isinstance(last_field, BooleanField):
            values = [*map(last_field.to_python, values)]

        query = operator.get_q(
            model=self._model,
            field_name=self._field_name,
            values=values,
        )

        if operator.exclude:
            query.negate()  # TODO: move more code in operator ?? (see CustomFieldConditionHandler)

        return query


class DateFieldHandlerMixin:
    def __init__(self, *, date_range=None, start=None, end=None):
        self._range_name = date_range
        self._start = start
        self._end = end

    @classmethod
    def _build_daterange_dict(cls, date_range=None, start=None, end=None):
        """Get a serializable dictionary corresponding to a
        <creme_core.utils.date_range.DateRange>.
        """
        range_dict = {}

        if date_range:
            if not date_range_registry.get_range(date_range):
                raise cls.ValueError(
                    f'{cls.__name__}.build_daterange_dict(): invalid date range.'
                )

            range_dict['name'] = date_range
        else:
            if start:
                range_dict['start'] = date_2_dict(start)

            if end:
                range_dict['end'] = date_2_dict(end)

        if not range_dict:
            raise cls.ValueError('date_range or start/end must be given.')

        return range_dict

    def _datefield_description(self, verbose_field):
        # TODO: move to DateRange ??
        if self._range_name:
            return _('«{field}» is «{value}»').format(
                field=verbose_field,
                value=self._get_date_range().verbose_name,
            )

        start = self._start
        end   = self._end

        if start:
            return (
                _('«{field}» is between «{start}» and «{end}»').format(
                    field=verbose_field,
                    start=date_format(start, 'DATE_FORMAT'),
                    end=date_format(end, 'DATE_FORMAT'),
                ) if end else
                _('«{field}» starts «{date}»').format(
                    field=verbose_field,
                    date=date_format(start, 'DATE_FORMAT'),
                )
            )

        if end:
            return _('«{field}» ends «{date}»').format(
                field=verbose_field,
                date=date_format(end, 'DATE_FORMAT'),
            )

        return '??'

    def _get_date_range(self):
        "Get a <creme_core.utils.date_range.DateRange> instance from the attributes."
        return date_range_registry.get_range(
            name=self._range_name, start=self._start, end=self._end,
        )

    @classmethod
    def _load_daterange_kwargs(cls, data):
        """Get a dictionary of arguments useful to retrieve a DateRange,
        from a serialized dictionary.

        Tip: build the serialized dictionary with <_build_daterange_dict()>.

        @param data: Dictionary. Used keys are: "name", "start", 'end".
        @return: Dictionary with potential keys: "date_range", "start", 'end".
        """
        if not isinstance(data, dict):
            raise cls.DataError(
                f'{cls.__name__}._load_daterange_kwargs() -> '
                f'invalid data ({data} is not a dict)'
            )

        get = data.get
        kwargs = {'date_range': get('name')}

        for key in ('start', 'end'):
            date_kwargs = get(key)
            if date_kwargs:
                if not isinstance(date_kwargs, dict):
                    raise cls.DataError(
                        f'{cls.__name__}._load_daterange_kwargs() -> '
                        f'invalid data ({date_kwargs} is not a dict)'
                    )

                try:
                    dt = datetime(**date_kwargs)
                except TypeError as e:
                    raise cls.DataError(
                        f'{cls.__name__}._load_daterange_kwargs() -> '
                        f'invalid data for date ({e})')
                else:
                    kwargs[key] = make_aware(dt)

        return kwargs


class DateRegularFieldConditionHandler(DateFieldHandlerMixin,
                                       BaseRegularFieldConditionHandler):
    """Filter entities by using one of their date fields."""
    type_id = 6

    def __init__(self, *, efilter_type, model, field_name, **kwargs):
        BaseRegularFieldConditionHandler.__init__(
            self, efilter_type=efilter_type, model=model, field_name=field_name,
        )
        DateFieldHandlerMixin.__init__(self, **kwargs)

    def accept(self, *, entity, user):
        return self._get_date_range().accept(
            value=self.field_info.value_from(entity), now=now(),
        )

    @classmethod
    def build(cls, *, efilter_type, model, name, data):
        return cls(
            efilter_type=efilter_type,
            model=model,
            field_name=name,
            **cls._load_daterange_kwargs(data),  # TODO: test errors (empty, other ?)
        )

    @classmethod
    def build_condition(cls, model, field_name,
                        date_range=None, start=None, end=None,
                        filter_type=EF_REGULAR,
                        condition_cls=EntityFilterCondition,
                        ):
        """Build an (unsaved) EntityFilterCondition.

        @param model: Class inheriting <creme_core.models.CremeEntity>.
        @param field_name: Name of the field.
        @param date_range: ID of a <creme_core.utils.date_range.DateRange> registered
               in <creme_core/utils/date_range.date_range_registry>, or None
               if a custom range is used.
        @param start: Instance of <datetime.date>, or None.
        @param end: Instance of <datetime.date>, or None.
        @param filter_type: see the field 'EntityFilter.filter_type'.
        @param condition_cls: Class of condition.

        If a custom range is used, at least one of the 2 argument "start" & "end"
        must be filled with a date.
        """
        error = cls._check_field(model=model, field_name=field_name)
        if error:
            raise cls.ValueError(error)

        return condition_cls(
            filter_type=filter_type,
            model=model,
            type=cls.type_id,
            name=field_name,
            value=cls._build_daterange_dict(date_range, start, end),
        )

    @staticmethod
    def _check_field(model, field_name):
        try:
            field_info = FieldInfo(model, field_name)
        except FieldDoesNotExist as e:
            return str(e)

        # TODO: test
        if not all(field.get_tag(FieldTag.VIEWABLE) for field in field_info):
            return f'{model.__name__}.{field_name} is not viewable'

        if not is_date_field(field_info[-1]):
            return f"'{field_name}' is not a date field"

    def description(self, user):
        return self._datefield_description(verbose_field=self.field_info.verbose_name)

    @property
    def error(self):
        return self._check_field(model=self._model, field_name=self._field_name)

    @classmethod
    def formfield(cls, form_class=ef_fields.DateFieldsConditionsField, **kwargs):
        defaults = {'label': _('On date fields'), **kwargs}

        return form_class(**defaults)

    def get_q(self, user):
        return Q(**self._get_date_range().get_q_dict(field=self._field_name, now=now()))


class BaseCustomFieldConditionHandler(FilterConditionHandler):
    _custom_field_uuid: UUID
    _custom_field: CustomField | None
    _related_name: str

    def __init__(self, *,
                 efilter_type,
                 model=None,
                 custom_field: CustomField | str,
                 related_name: str | None = None,
                 ):
        """Constructor.

        @param model: Class inheriting <creme_core.models.CremeEntity>
               (ignored if an EntityFilter instance is passed for "custom_field" -- see below).
        @param custom_field: <creme_core.models.CustomField> instance or UUID.
        @param related_name: Related name (django's way) corresponding to the
               used CustomField.
        """
        if isinstance(custom_field, CustomField):
            super().__init__(
                efilter_type=efilter_type,
                model=custom_field.content_type.model_class(),
            )
            self._custom_field_uuid = custom_field.uuid
            self._custom_field = custom_field
            self._related_name = custom_field.value_class.get_related_name()
        else:
            assert isinstance(custom_field, UUID)  # TODO: cast if string ?

            if model is None:
                raise TypeError(
                    'The argument "model" must be passed if a CustomField ID is passed.'
                )
            if related_name is None:
                raise TypeError(
                    'The argument "related_name" must be passed if a CustomField ID is passed.'
                )

            super().__init__(efilter_type=efilter_type, model=model)
            self._custom_field_uuid = custom_field
            self._custom_field = None
            self._related_name = related_name

    @property
    def applicable_on_entity_base(self):
        return True

    @property
    def custom_field(self) -> CustomField | bool:
        cfield = self._custom_field
        if cfield is None:
            self._custom_field = cfield = next(
                (
                    cfield
                    for cfield in CustomField.objects.get_for_model(self.model).values()
                    if cfield.uuid == self._custom_field_uuid
                ),
                False
            )

        return cfield

    @property
    def error(self):
        rname = self._related_name
        if not any(rname == cf_cls.get_related_name() for cf_cls in _TABLES.values()):
            return f"related_name '{rname}' is invalid"

        # TODO: check existence of the CustomField ? (normally the condition should be removed)

    @classmethod
    def query_for_related_conditions(cls, instance):
        return Q(
            type=cls.type_id,
            name=str(instance.uuid),
        ) if isinstance(instance, CustomField) else Q()


class CustomFieldConditionHandler(OperatorConditionHandlerMixin,
                                  BaseCustomFieldConditionHandler):
    """Filter entities by using one of their CustomFields.
    Note: no date field ; see DateCustomFieldConditionHandler
    """
    type_id = 20

    def __init__(self, *,
                 efilter_type,
                 model=None, custom_field,
                 related_name=None, operator_id, values,
                 ):
        """Constructor.

        @param model: See <BaseCustomFieldConditionHandler>.
        @param custom_field: See <BaseCustomFieldConditionHandler>.
        @param related_name: See <BaseCustomFieldConditionHandler>.
        @param operator_id: ID of operator
               (see <creme_core.core.entity_filter.operators.OPERATORS>).
        @param values: List of values to filter with.
        """
        super().__init__(
            efilter_type=efilter_type, model=model,
            custom_field=custom_field, related_name=related_name,
        )
        self._operator_id = operator_id
        self._values = values
        self._verbose_values = None  # Cache for values in description()

    def accept(self, *, entity, user):
        operator = self.get_operator(self._operator_id)
        values = self._values

        cfield = self.custom_field
        cfvalue = entity.get_custom_value(cfield)
        cf_type = cfield.field_type

        if cfvalue is None:
            field_value = None
        else:
            # TODO: current form-field/widget generates the JSON '["True"]' or '["123"]',
            #       when '[true]' or '[123]' would be better  => fix form & migrate data
            if cf_type in {CustomField.INT, CustomField.ENUM, CustomField.MULTI_ENUM}:
                # TODO: move to operator code (the code works without this test,
                #       because boolean are just converted to integers, but it's crappy)
                if not isinstance(operator, operators.IsEmptyOperator):
                    values = [*map(int, values)]
            elif cf_type == CustomField.BOOL:
                values = [*map(BooleanField().to_python, values)]
            elif cf_type == CustomField.FLOAT:
                values = [*map(Decimal, values)]

            if cf_type == CustomField.MULTI_ENUM:
                # NB: we use get_enumvalues() to get a cached result & avoid re-making queries
                field_value = [v.id for v in cfvalue.get_enumvalues()]
            elif cf_type == CustomField.ENUM:
                field_value = cfvalue.value_id
            else:
                field_value = cfvalue.value

        accept = partial(operator.accept, values=values)

        return (
            any(accept(field_value=i) for i in field_value)
            if isinstance(field_value, list) else
            accept(field_value=field_value)
        )

    @classmethod
    def build(cls, *, efilter_type, model, name, data):
        try:
            cf_uuid = UUID(name)
            kwargs = {
                'operator_id':  int(data['operator']),
                'related_name': data['rname'],  # NB: we could remove it...
                'values':       data['values'],  # TODO: check if it's a list ? check content ?
            }
        except (TypeError, KeyError, ValueError) as e:
            raise cls.DataError(
                f'{cls.__name__}.build(): invalid data ({e})'
            )

        return cls(efilter_type=efilter_type, model=model, custom_field=cf_uuid, **kwargs)

    @classmethod
    def build_condition(cls, *, custom_field, operator, values,
                        user=None,
                        filter_type=EF_REGULAR,
                        condition_cls=EntityFilterCondition,
                        ):
        """Build an (unsaved) EntityFilterCondition.

        @param custom_field: Instance of <creme_core.models.CustomField>.
        @param operator: <creme_core.core.entity_filter.operators.ConditionOperator> ID or class.
        @param values: List of searched values (logical OR between them).
               Exceptions: - RANGE: 'values' is always a list of 2 elements
                           - ISEMPTY: 'values' is a list containing one boolean.
        @param user: Some fields need a user instance for permission validation.
        @param filter_type: see the field 'EntityFilter.filter_type'.
        @param condition_cls: Class of condition.
        """
        operator_id = operator if isinstance(operator, int) else operator.type_id

        operator_obj = entity_filter_registries[filter_type].get_operator(operator_id)

        if operator_obj is None:
            raise cls.ValueError(
                f'{cls.__name__}.build_condition(): unknown operator ID="{operator_id}"'
            )

        if custom_field.field_type in (CustomField.DATE, CustomField.DATETIME):
            raise cls.ValueError(
                f'{cls.__name__}.build_condition(): does not manage DATE/DATETIME CustomFields'
            )

        # TODO: A bit ugly way to validate operators, but needed for compatibility.
        if (
            custom_field.field_type == CustomField.BOOL
            and operator_id not in (
                operators.EQUALS, operators.EQUALS_NOT, operators.ISEMPTY,
            )
        ):
            raise cls.ValueError(
                f'{cls.__name__}.build_condition(): BOOL type is only compatible with '
                f'EQUALS, EQUALS_NOT and ISEMPTY operators'
            )
            # TODO: validate values is a list containing one Boolean (done
            #       below for ISEMPTY only) when form field has been fixed

        if not isinstance(values, list | tuple):
            raise cls.ValueError(
                f'{cls.__name__}.build_condition(): value is not an array'
            )

        cf_value_class = custom_field.value_class

        try:
            # TODO: move this in Operator code
            if operator_id == operators.ISEMPTY:
                value = operator_obj.validate_field_values(
                    field=None, values=values, user=user,
                    efilter_registry=cls.efilter_registry,
                )
            else:
                clean_value = cf_value_class.get_formfield(custom_field, None, user=user).clean

                if custom_field.field_type == CustomField.MULTI_ENUM:
                    value = [str(clean_value([v])[0]) for v in values]
                else:
                    value = [str(clean_value(v)) for v in values]
        except ValidationError as e:
            raise cls.ValueError(
                gettext('Condition on field «{field}»: {error}').format(
                    field=custom_field.name,
                    error='\n'.join(e.messages),
                )
            ) from e
        except Exception as e:
            raise cls.ValueError(str(e)) from e

        return condition_cls(
            filter_type=filter_type,
            model=custom_field.content_type.model_class(),
            type=cls.type_id,
            name=str(custom_field.uuid),
            value={
                'operator': operator_id,
                'values':   value,
                'rname':    cf_value_class.get_related_name(),
            },
        )

    def description(self, user):
        cfield = self.custom_field
        if cfield is False:
            # NB: should not happen because EntityFilterCondition with errors are removed.
            return '???'

        values = self._verbose_values
        if values is None:
            if cfield.field_type in {CustomField.ENUM, CustomField.MULTI_ENUM}:
                try:
                    values = [*CustomFieldEnumValue.objects.filter(pk__in=self._values)]
                except ValueError:
                    logger.exception(
                        'Error in %s.description() while retrieving '
                        'CustomField enum-values with ID=%s',
                        type(self).__name__, self._values,
                    )
                    values = ['???']
            else:
                values = self._values

            self._verbose_values = values

        return self.get_operator(self._operator_id).description(
            field_vname=cfield.name,
            values=values,
        )

    @property
    def error(self):
        return self._check_operator(self._operator_id) or super().error

    @classmethod
    def formfield(cls, form_class=ef_fields.CustomFieldsConditionsField, **kwargs):
        defaults = {'label': _('On custom fields'), **kwargs}

        return form_class(**defaults)

    def get_q(self, user):
        # NB: Sadly we retrieve the ids of the entity that match with this condition
        #     instead of use a 'JOIN', in order to avoid the interaction between
        #     several conditions on the same type of CustomField (i.e. same table).
        operator = self.get_operator(self._operator_id)
        related_name = self._related_name
        fname = f'{related_name}__value'
        values = self._values
        resolved_values = self.resolve_operands(values=values, user=user)

        # TODO: move more code in operator ??
        if isinstance(operator, operators.IsEmptyOperator):
            query = Q(**{f'{related_name}__isnull': resolved_values[0]})
        else:
            query = Q(**{f'{related_name}__custom_field': self.custom_field})
            key = operator.key_pattern.format(fname)
            value_q = Q()

            for value in resolved_values:
                value_q |= Q(**{key: value})

            query &= value_q

        if operator.exclude:
            query.negate()  # TODO: move this in operator ??

        return Q(
            pk__in=self._model
                       ._default_manager
                       .filter(query)
                       .values_list('id', flat=True),
        )


class DateCustomFieldConditionHandler(DateFieldHandlerMixin,
                                      BaseCustomFieldConditionHandler):
    """Filter entities by using one of their date CustomFields."""
    type_id = 21

    def __init__(self, *,
                 efilter_type, model=None,
                 custom_field, related_name=None,
                 **kwargs):
        """Constructor.

        @param model: See <BaseCustomFieldConditionHandler>.
        @param custom_field: See <BaseCustomFieldConditionHandler>.
        @param related_name: See <BaseCustomFieldConditionHandler>.
        @param date_range: See <DateFieldHandlerMixin>.
        @param start: See <DateFieldHandlerMixin>.
        @param end: See <DateFieldHandlerMixin>.
        """
        BaseCustomFieldConditionHandler.__init__(
            self, efilter_type=efilter_type, model=model,
            custom_field=custom_field, related_name=related_name,
        )
        DateFieldHandlerMixin.__init__(self, **kwargs)

    def accept(self, *, entity, user):
        cfvalue = entity.get_custom_value(self.custom_field)

        return self._get_date_range().accept(
            value=cfvalue.value if cfvalue else None,
            now=now(),
        )

    @classmethod
    def build(cls, *, efilter_type, model, name, data):
        kwargs = cls._load_daterange_kwargs(data)  # It tests if it's a dict too
        try:
            cf_id = UUID(name)
            rname = data['rname']
        except (KeyError, ValueError) as e:
            raise cls.DataError(
                f'{cls.__name__}.build(): invalid data ({e})'
            )

        return cls(
            efilter_type=efilter_type, model=model, custom_field=cf_id, related_name=rname,
            **kwargs
        )

    @classmethod
    def build_condition(cls, *, custom_field,
                        date_range=None, start=None, end=None,
                        filter_type=EF_REGULAR,
                        condition_cls=EntityFilterCondition,
                        ):
        """Build an (unsaved) EntityFilterCondition.

        @param custom_field: Instance of <creme_core.models.CustomField>
               with the type <CustomField.DATETIME>.
        @param date_range: ID of a <creme_core.utils.date_range.DateRange> registered
               in <creme_core/utils/date_range.date_range_registry>, or None
               if a custom range is used.
        @param start: Instance of <datetime.date>, or None.
        @param end: Instance of <datetime.date>, or None.
        @param filter_type: see the field 'EntityFilter.filter_type'.
        @param condition_cls: Class of condition.

        If a custom range is used, at least one of the 2 argument "start" & "end"
        must be filled with a date.
        """
        if custom_field.field_type not in (CustomField.DATE, CustomField.DATETIME):
            raise cls.ValueError(
                f'{cls.__name__}.build_condition(): not a date custom field.'
            )

        value = cls._build_daterange_dict(date_range, start, end)
        value['rname'] = custom_field.value_class.get_related_name()

        return condition_cls(
            filter_type=filter_type,
            model=custom_field.content_type.model_class(),
            type=cls.type_id,
            name=str(custom_field.uuid),
            value=value,
        )

    def description(self, user):
        cfield = self.custom_field
        if cfield is False:
            # NB: should not happen because EntityFilterCondition with errors are removed.
            return '???'

        return self._datefield_description(verbose_field=cfield.name)

    @classmethod
    def formfield(cls, form_class=ef_fields.DateCustomFieldsConditionsField, **kwargs):
        defaults = {'label': _('On date custom fields'), **kwargs}

        return form_class(**defaults)

    def get_q(self, user):
        # NB: see CustomFieldConditionHandler.get_q() remark
        related_name = self._related_name
        fname = f'{related_name}__value'

        q_dict = self._get_date_range().get_q_dict(field=fname, now=now())
        q_dict[f'{related_name}__custom_field'] = self.custom_field

        return Q(
            pk__in=self._model
                       ._default_manager
                       .filter(**q_dict)
                       .values_list('id', flat=True),
        )


class BaseRelationConditionHandler(FilterConditionHandler):
    def __init__(self, *, efilter_type, model, rtype, exclude):
        super().__init__(efilter_type=efilter_type, model=model)
        self._exclude = exclude

        if isinstance(rtype, RelationType):
            self._rtype_id = rtype.id
            self._rtype = rtype
        else:
            self._rtype_id = rtype
            self._rtype = None

    @property
    def applicable_on_entity_base(self):
        return True

    @classmethod
    def query_for_related_conditions(cls, instance):
        return Q(
            type=cls.type_id,
            name=instance.id,
        ) if isinstance(instance, RelationType) else Q()

    @property
    def relation_type(self) -> RelationType | bool:
        rtype = self._rtype
        if rtype is None:
            self._rtype = rtype = (
                RelationType.objects.filter(id=self._rtype_id).first() or False
            )

        return rtype


class RelationConditionHandler(BaseRelationConditionHandler):
    """Filter entities which are have (or have not) certain Relations."""
    type_id = 10

    # NB: True == exclude
    DESCRIPTION_FORMATS = {
        'rtype': {
            False: _('The entities have relationships «{predicate}»'),
            True:  _('The entities have no relationship «{predicate}»'),
        },
        'ctype': {
            False: _('The entities have relationships «{predicate}» to «{model}»'),
            True: _('The entities have no relationship «{predicate}» to «{model}»'),
        },
        'entity': {
            False: _('The entities have relationships «{predicate}» to «{entity}»'),
            True:  _('The entities have no relationship «{predicate}» to «{entity}»'),
        },
    }

    _entity: CremeEntity | None | Literal[False]

    def __init__(self, *, model, rtype,
                 efilter_type,
                 exclude=False,
                 ctype: ContentType | tuple[str, str] | None = None,
                 entity: UUID | None = None,
                 ):
        super().__init__(
            efilter_type=efilter_type, model=model, rtype=rtype, exclude=exclude,
        )

        if isinstance(entity, CremeEntity):
            self._entity_uuid = entity.uuid
            self._entity = entity
            self._ct_key = None
        else:
            self._entity_uuid = entity
            self._entity = None
            self._ct_key = ctype.natural_key() if isinstance(ctype, ContentType) else ctype

    def accept(self, *, entity, user):
        # NB: we use get_relations() in order to get a cached result, & so avoid
        #     additional queries when calling several times this method.
        # TODO: add a system to populate relations when checking several entities
        relations = entity.get_relations(relation_type_id=self._rtype_id)

        if self._entity_uuid:
            entity = self.entity
            entity_id = entity.id if entity else None
            found = any(r.object_entity_id == entity_id for r in relations)
        elif self._ct_key:
            ct = self.content_type
            ct_id = ct.id if ct else None
            # TODO: get_relations() with real_obj_entities==False does not select_related()
            #       => real_obj_entities = True ?
            #          select_related() even if real_obj_entities==False ?
            #          CT's ID stored in Relation (RealEntityForeignKey) ??
            found = any(r.object_entity.entity_type_id == ct_id for r in relations)
        else:
            found = bool(relations)

        return not found if self._exclude else found

    @classmethod
    def build(cls, *, efilter_type, model, name, data):
        if not isinstance(data, dict):
            raise cls.DataError(f'{cls.__name__}.build(): data must be a dictionary')

        try:
            has = data['has']
        except KeyError as e:
            raise cls.DataError(f'{cls.__name__}.build(): missing value "has"') from e

        if not isinstance(has, bool):
            raise cls.DataError(f'{cls.__name__}.build(): "has" is not a boolean')

        # ---
        ct_key = data.get('ct')
        if ct_key is not None:
            # TODO: separated function?
            if not isinstance(ct_key, str):
                raise cls.DataError(f'{cls.__name__}.build(): "ct" is not a string')

            ct_key = ct_key.split('.', 1)

            if len(ct_key) != 2:
                raise cls.DataError(f'{cls.__name__}.build(): "ct" is not a valid key')

        # ---
        entity_uuid = data.get('entity')
        if entity_uuid is not None:
            try:
                entity_uuid = UUID(entity_uuid)
            except ValueError as e:
                raise cls.DataError(
                    f'{cls.__name__}.build(): "entity" is not a valid uuid ({e})'
                ) from e

        return cls(
            efilter_type=efilter_type,
            model=model,
            rtype=name,
            exclude=not has,
            ctype=ct_key,
            entity=entity_uuid,
        )

    @classmethod
    def build_condition(cls, *, model, rtype, has=True, ct=None, entity=None,
                        filter_type=EF_REGULAR,
                        condition_cls=EntityFilterCondition,
                        ):
        """Build an (unsaved) EntityFilterCondition.

        @param model: Class inheriting <creme_core.models.CremeEntity>.
        @param rtype: Instance of <creme_core.models.RelationType>.
        @param has: Boolean indicating if the filtered entities have (<True>)
               or have not (<False>) the wanted Relations.
        @param ct: Instance of <django.contrib.contenttypes.models.ContentType>,
               or None. If given, only Relations with entities with this type
               are examined.
        @param entity: Instance of <creme_core.models.CremeEntity>, or None.
               If given, only Relations with this entity are examined.
               Note: "ct" argument is not used if this argument is given.
        @param filter_type: see the field 'EntityFilter.filter_type'.
        @param condition_cls: Class of condition.
        """
        value = {'has': bool(has)}

        if entity:
            value['entity'] = str(entity.uuid)
        elif ct:
            # TODO: factorise with creme_config exporter?
            value['ct'] = '.'.join(ct.natural_key())

        return condition_cls(
            filter_type=filter_type,
            model=model,
            type=cls.type_id,
            name=rtype.id,
            value=value,
        )

    @property
    def content_type(self) -> ContentType | None | bool:
        ct_key = self._ct_key
        try:
            return ContentType.objects.get_by_natural_key(*ct_key) if ct_key else None
        except ContentType.DoesNotExist:
            return False

    def description(self, user):
        rtype = self.relation_type
        if rtype is False:
            return '???'

        fmt_kwargs = {'predicate': rtype.predicate}
        entity = self.entity

        if entity is not None:
            fmt_kwargs['entity'] = entity.allowed_str(user) if entity else '???'
            str_key = 'entity'
        else:
            ctype = self.content_type

            if ctype is not None:
                fmt_kwargs['model'] = (
                    model_verbose_name_plural(ctype.model_class())
                    if ctype else
                    '???'
                )
                str_key = 'ctype'
            else:
                str_key = 'rtype'

        return self.DESCRIPTION_FORMATS[str_key][self._exclude].format(**fmt_kwargs)

    @property
    def entity(self) -> CremeEntity | None | Literal[False]:
        if self._entity_uuid is None:
            return None

        entity = self._entity
        if entity is None:
            e = CremeEntity.objects.filter(uuid=self._entity_uuid).first()
            self._entity = entity = e.get_real_entity() if e is not None else False

        return entity

    @classmethod
    def formfield(cls, form_class=ef_fields.RelationsConditionsField, **kwargs):
        defaults = {
            'label': _('On relationships'),
            'help_text': _(
                'Do not select any entity if you want to match them all.'
            ),
            **kwargs
        }

        return form_class(**defaults)

    # TODO: use a filter "relations__*" when there is only one condition on Relations?
    #       + update code of 'entities_are_distinct()'
    def get_q(self, user):
        kwargs = {'type': self._rtype_id}

        if self._entity_uuid:
            kwargs['object_entity'] = self.entity.id if self.entity else 0
        elif self._ct_key:
            kwargs['object_entity__entity_type'] = self.content_type

        query = Q(
            pk__in=Relation.objects
                           .filter(**kwargs)
                           .values_list('subject_entity_id', flat=True),
        )

        if self._exclude:
            query.negate()

        return query


class RelationSubFilterConditionHandler(BaseRelationConditionHandler):
    """Filter entities which are have (or have not) certain Relations.
    with entities filtered by a sub EntityFilter.
    """
    type_id = 11

    # NB: True == exclude
    DESCRIPTION_FORMATS = {
        False: _('The entities have relationships «{predicate}» to «{filter}»'),
        True:  _('The entities have no relationship «{predicate}» to «{filter}»'),
    }

    def __init__(self, *, efilter_type, model, rtype, subfilter, exclude=False):
        """Constructor.

        @param efilter_type: See <creme_core.models.EntityFilter.filter_type>.
        @param model: Class inheriting <creme_core.models.CremeEntity>.
        @param rtype: <creme_core.models.RelationType> instance or ID (string).
        @param subfilter: <creme_core.models.EntityFilter> instance or ID (string).
        @param exclude: Boolean ; the retrieved Relations have to be
               included (True) or excluded (False).
        """
        super().__init__(
            efilter_type=efilter_type, model=model, rtype=rtype, exclude=exclude,
        )

        if isinstance(subfilter, EntityFilter):
            self._subfilter_id = subfilter.id
            self._subfilter    = subfilter  # TODO: copy ?
        else:
            self._subfilter_id = subfilter

        self._exclude = exclude

    # def accept(self, *, entity, user):  TODO ? (not needed currently for credentials filters)

    @classmethod
    def build(cls, *, efilter_type, model, name, data):
        try:
            filter_id = data['filter_id']
            has = data['has']
        except (TypeError, KeyError) as e:
            raise cls.DataError(f'{cls.__name__}.build(): invalid data ({e})')

        if not isinstance(has, bool):
            raise cls.DataError(f'{cls.__name__}.build(): "has" is not a boolean')

        return cls(
            efilter_type=efilter_type, model=model,
            rtype=name, subfilter=filter_id, exclude=not has,
        )

    @classmethod
    def build_condition(cls, *, model, rtype, subfilter, has=True,
                        filter_type=EF_REGULAR,  # TODO: rename "efilter_type" for consistency?
                        condition_cls=EntityFilterCondition,
                        ):
        """Build an (unsaved) EntityFilterCondition.

        @param model: Class inheriting <creme_core.models.CremeEntity>.
        @param rtype: Instance of <creme_core.models.RelationType>.
        @param subfilter: Instance of <creme_core.models.models.EntityFilter>.
        @param has: Boolean indicating if the filtered entities have (<True>)
               or have not (<False>) the retrieved Relations.
        @param filter_type: see the field 'EntityFilter.filter_type'.
        @param condition_cls: Class of condition.
        """
        assert isinstance(subfilter, EntityFilter), type(subfilter)
        has = bool(has)

        return condition_cls(
            filter_type=filter_type,
            model=model,
            type=cls.type_id,
            name=rtype.id,
            value={'has': has, 'filter_id': subfilter.id},
            # NB: avoid a query to retrieve again the sub-filter (in forms).
            # TODO: assert this class is available in the registry ?
            handler=cls(
                efilter_type=filter_type, model=model,
                rtype=rtype, subfilter=subfilter, exclude=not has,
            ),
        )

    def description(self, user):
        rtype = self.relation_type

        return self.DESCRIPTION_FORMATS[self._exclude].format(
            predicate=rtype.predicate,
            filter=self.subfilter or '???',
        ) if rtype else '???'

    @property
    def error(self):
        # TODO: error if relation type not found ?
        if self.subfilter is False:
            return f"'{self.subfilter_id}' is not a valid filter ID"

    @classmethod
    def formfield(cls, form_class=ef_fields.RelationSubfiltersConditionsField, **kwargs):
        defaults = {
            'label': _('On relationships with results of other filters'),
            **kwargs
        }

        return form_class(**defaults)

    # TODO: use a filter "relations__*" when there is only one condition on Relations ??
    def get_q(self, user):
        subfilter = self.subfilter
        filtered = subfilter.filter(
            subfilter.entity_type.get_all_objects_for_this_type(),
        ).values_list('id', flat=True)

        query = Q(
            pk__in=Relation.objects
            .filter(type=self._rtype_id, object_entity__in=filtered)
            .values_list('subject_entity_id', flat=True),
        )

        if self._exclude:
            query.negate()

        return query

    @classmethod
    def query_for_parent_conditions(cls, ctype):
        # NB: we do not use "ctype" because an EntityFilter on a model can have
        #     a RelationSubFilterConditionHandler on another model.
        return Q(type=cls.type_id)

    @property
    def subfilter_id(self):
        return self._subfilter_id


# NB: we do not check existence of CremePropertyType in @error to avoid a query ;
#     the related EntityFilterCondition should be deleted if the
#     CremePropertyType is deleted.
class PropertyConditionHandler(FilterConditionHandler):
    """Filter entities which are have (or have not) certain CremeProperties."""
    type_id = 15

    # NB: True == exclude
    DESCRIPTION_FORMATS = {
        False: _('The entities have the property «{}»'),
        True:  _('The entities have no property «{}»'),
    }

    _ptype: CremePropertyType | None | Literal[False]

    def __init__(self, *,
                 efilter_type: str,
                 model: type[CremeEntity],
                 ptype: CremePropertyType | UUID | str,
                 exclude=False,
                 ):
        """Constructor.

        @param efilter_type: See <creme_core.models.EntityFilter.filter_type>.
        @param model: Class inheriting <creme_core.models.CremeEntity>.
        @param ptype: CremeProperty type. Can be passed on the form of its UUID.
        @param exclude: Boolean ; the retrieved CremeProperties have to be
               included (True) or excluded (False).
        """
        super().__init__(efilter_type=efilter_type, model=model)
        if isinstance(ptype, CremePropertyType):
            self._ptype_uuid = ptype.uuid
            self._ptype = ptype
        else:
            self._ptype_uuid = ptype if isinstance(ptype, UUID) else UUID(ptype)
            self._ptype = None

        self._exclude = exclude

    def accept(self, *, entity, user):
        ptype_uuid = self._ptype_uuid
        # NB: we use get_properties() in order to get a cached result, & so avoid
        #     additional queries when calling several times this method.
        # TODO: add a system to populate properties when checking several entities
        accepted = any(prop.type.uuid == ptype_uuid for prop in entity.get_properties())

        return not accepted if self._exclude else accepted

    @property
    def applicable_on_entity_base(self):
        return True

    @classmethod
    def build(cls, *, efilter_type, model, name, data):
        try:
            has = data['has']
        except (TypeError, KeyError) as e:
            raise cls.DataError(f'{cls.__name__}.build(): invalid data ({e})')

        if not isinstance(has, bool):
            raise cls.DataError(f'{cls.__name__}.build(): "has" is not a boolean')

        return cls(
            efilter_type=efilter_type, model=model, ptype=name, exclude=(not has),
        )

    @classmethod
    def build_condition(cls, *, model, ptype, has=True,
                        filter_type=EF_REGULAR,
                        condition_cls=EntityFilterCondition,
                        ):
        """Build an (unsaved) EntityFilterCondition.

        @param model: Class inheriting <creme_core.models.CremeEntity>.
        @param ptype: Instance of <creme_core.models.CremePropertyType>.
        @param has: Boolean indicating if the filtered entities have (<True>)
               or have not (<False>) the retrieved CremeProperties.
        @param filter_type: see the field 'EntityFilter.filter_type'.
        @param condition_cls: Class of condition.
        """
        return condition_cls(
            filter_type=filter_type,
            model=model,
            type=cls.type_id,
            name=str(ptype.uuid),
            value={'has': bool(has)},
        )

    def description(self, user):
        ptype = self.property_type
        return self.DESCRIPTION_FORMATS[self._exclude].format(ptype) if ptype else '???'

    @classmethod
    def formfield(cls, form_class=ef_fields.PropertiesConditionsField, **kwargs):
        defaults = {'label': _('On properties'), **kwargs}

        return form_class(**defaults)

    # TODO: see remark on RelationConditionHandler._get_q()
    def get_q(self, user):
        query = Q(
            pk__in=CremeProperty.objects
                                .filter(type__uuid=self._ptype_uuid)
                                .values_list('creme_entity_id', flat=True),
        )

        # Do we filter entities which has got or has not got the property type ?
        if self._exclude:
            query.negate()

        return query

    @property
    def property_type(self) -> CremePropertyType | bool:
        ptype = self._ptype
        if ptype is None:
            self._ptype = ptype = CremePropertyType.objects.filter(
                uuid=self._ptype_uuid,
            ).first() or False

        return ptype

    @classmethod
    def query_for_related_conditions(cls, instance):
        return Q(
            type=cls.type_id,
            name=instance.uuid,
        ) if isinstance(instance, CremePropertyType) else Q()


all_handlers: tuple[type[FilterConditionHandler], ...] = (
    RegularFieldConditionHandler,
    DateRegularFieldConditionHandler,

    CustomFieldConditionHandler,
    DateCustomFieldConditionHandler,

    RelationConditionHandler,
    RelationSubFilterConditionHandler,

    PropertyConditionHandler,

    SubFilterConditionHandler,
)
