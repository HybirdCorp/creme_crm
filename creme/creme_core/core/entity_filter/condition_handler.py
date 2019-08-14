# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

from datetime import datetime

from django.contrib.contenttypes.models import ContentType
from django.db.models import BooleanField, Q, ManyToManyField
from django.db.models.fields import FieldDoesNotExist
from django.utils.timezone import now

from creme.creme_core.models import (
    CremeEntity,
    CremePropertyType, CremeProperty,
    CustomField, CustomFieldBoolean,
    EntityFilter, EntityFilterCondition,
    RelationType, Relation,
)
from creme.creme_core.models.custom_field import _TABLES
from creme.creme_core.utils.date_range import date_range_registry
from creme.creme_core.utils.dates import make_aware_dt, date_2_dict
from creme.creme_core.utils.meta import is_date_field, FieldInfo

from . import operators, entity_filter_registry


class FilterConditionHandler:
    """A condition handler is linked to an instance of
    <creme_core.models.EntityFilterCondition> & provide the behaviour specific
    to the condition type.

    The main feature is provided by the method 'get_q()' ; generating a
    <django.models.Q> object to filter entities by one of their model-field or
    by the presence of a CremeProperty are different behaviours of course.
    These behaviours are implemented in child-classes.

    All child-classes are registered in
    <creme_core.core.entity_filter.entity_filter_registry>.
    """
    type_id = None

    class DataError(Exception):
        pass

    class ValueError(Exception):
        pass

    def __init__(self, model):
        """Constructor.

        @param model: class inheriting <creme_core.models.CremeEntity>.
        """
        self._model = model
        self._subfilter = None   # 'None' means not retrieved ; 'False' means invalid filter

    @classmethod
    def build(cls, *, model, name, data):
        "Get an instance of FilterConditionHandler from serialized data."
        raise NotImplementedError

    def entities_are_distinct(self):
        return True

    @property
    def error(self):
        """Get error corresponding to invalid data contained in the condition.
        @return: A string if there is an error, or None.
        """
        return None

    def get_q(self, user):
        """Get the query which filter the entities with the expected behaviour.

        @param user: <django.contrib.auth.get_user_model()> instance ;
               used to check credentials.
        @return: An instance of <django.models.Q>.
        """
        raise NotImplementedError()

    @property
    def model(self):
        return self._model

    @classmethod
    def query_for_related_conditions(cls, instance):
        """"Get a Q instance to retrieve EntityFilterConditions which are
        related to an instance.
        It's useful to delete useless conditions (their related instance is deleted).
        """
        return Q()

    @classmethod
    def query_for_parent_conditions(cls, ctype):
        """"Get a Q instance to retrieve EntityFilterConditions which have
        potentially sub-filters for a given ContentType.
        It's useful to build EntityFilters tree (to check cycle etc...).
        """
        return Q()

    @property
    def subfilter(self):
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
    def subfilter_id(self):
        "@return: An ID of an EntityFilter, or None."
        return None


class SubFilterConditionHandler(FilterConditionHandler):
    """Filter entities with a (sub) EntityFilter."""
    type_id = 1

    def __init__(self, *, model=None, subfilter):
        """Constructor.

        @param model: Class inheriting <creme_core.models.CremeEntity>
               (ignored if an EntityFilter instance is passed for "subfilter" -- see below).
        @param subfilter: <creme_core.models.EntityFilter> instance or ID (string).
        """
        if isinstance(subfilter, EntityFilter):
            super().__init__(model=subfilter.entity_type.model_class())
            self._subfilter_id = subfilter.id
            self._subfilter    = subfilter  # TODO: copy ?
        else:
            if model is None:
                raise TypeError(
                    'The argument "model" must be passed if a filter ID is passed.'
                )

            super().__init__(model=model)
            self._subfilter_id = subfilter

    @classmethod
    def build(cls, *, model, name, data):
        return cls(model=model, subfilter=name)

    @classmethod
    def build_condition(cls, subfilter, condition_cls=EntityFilterCondition):
        """Build an (unsaved) EntityFilterCondition.

        @param subfilter: <creme_core.models.EntityFilter> instance.
        @param condition_cls: Class of condition.
        """
        assert isinstance(subfilter, EntityFilter)

        return condition_cls(
            type=cls.type_id,
            model=subfilter.entity_type.model_class(),
            name=subfilter.id,
            # NB: avoid a query to retrieve again the sub-filter (in forms).
            handler=cls(subfilter=subfilter),
        )

    @property
    def error(self):
        if self.subfilter is False:
            return "'{}' is not a valid filter ID".format(self.subfilter_id)

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
    @staticmethod
    def _check_operator(operator_id):
        if operator_id not in operators.OPERATORS:
            return "Operator ID '{}' is invalid".format(operator_id)

    @staticmethod
    def resolve_operand(value, user):
        "Replace a value corresponding to a special dynamic operand if needed."
        operand = entity_filter_registry.get_operand(type_id=value, user=user)

        return value if operand is None else operand.resolve()


class RegularFieldConditionHandler(OperatorConditionHandlerMixin,
                                   FilterConditionHandler,
                                  ):
    """Filter entities by using one of their fields.
    Note: no date field ; see <DateRegularFieldConditionHandler>.
    """
    type_id = 5
    operators = operators.OPERATORS

    def __init__(self, *, model, field_name, operator_id, values):
        super().__init__(model=model)
        self._field_name = field_name
        self._operator_id = operator_id
        self._values = values

    # TODO: multi-value is stupid for some operator (LT, GT etc...) => improve checking ???
    @classmethod
    def build(cls, *, model, name, data):
        try:
            kwargs = {
                'operator_id': int(data['operator']),
                'values':      data['values'],
            }
        except (TypeError, KeyError, ValueError) as e:
            raise cls.DataError(
                '{}.build(): invalid data ({})'.format(cls.__name__, e)
            )

        return cls(model=model, field_name=name, **kwargs)

    @classmethod
    def build_condition(cls, *, model, field_name, operator_id, values, user=None,
                        condition_cls=EntityFilterCondition,
                        efilter_registry=entity_filter_registry,
                       ):
        """Build an (unsaved) EntityFilterCondition.

        @param model: Class inheriting <creme_core.models.CremeEntity>.
        @param field_name: Name of the field.
        @param operator_id: Operator ID ;
               see 'creme_core.core.entity_filter.operators.EQUALS' and friends.
        @param values: List of searched values (logical OR between them).
               Exceptions: - RANGE: 'values' is always a list of 2 elements
                           - ISEMPTY: 'values' is a list containing one boolean.
        @param user: Some fields need a user instance for permission validation.
        @param condition_cls: Class of condition.
        @param efilter_registry: Instance of <_EntityFilterRegistry>.
        """
        try:
            operator_obj = cls.operators[operator_id]
        except KeyError:
            raise cls.ValueError(
                '{}.build_condition(): unknown operator "{}"'.format(
                    cls.__name__, operator_id,
                )
            )

        try:
            finfo = FieldInfo(model, field_name)
        except FieldDoesNotExist as e:
            raise cls.ValueError(str(e)) from e

        try:
            values = operator_obj.validate_field_values(
                field=finfo[-1], values=values, user=user,
                efilter_registry=efilter_registry,
            )
        except Exception as e:
            raise cls.ValueError(str(e)) from e

        return condition_cls(
            model=model,
            type=cls.type_id,
            name=field_name,
            value=condition_cls.encode_value(
                {'operator': operator_id, 'values': values}
            ),
        )

    def entities_are_distinct(self):
        field_info = FieldInfo(self._model, self._field_name)

        return not isinstance(field_info[0], ManyToManyField)

    @property
    def error(self):
        try:
            FieldInfo(self._model, self._field_name)
        except FieldDoesNotExist as e:
            return str(e)

        return self._check_operator(self._operator_id)

    def get_q(self, user):
        operator = operators.OPERATORS[self._operator_id]
        resolve = self.resolve_operand
        values = [resolve(value, user) for value in self._values]
        field_info = FieldInfo(self._model, self._field_name)

        # HACK: old format compatibility for boolean fields.
        if isinstance(field_info[-1], BooleanField):
            clean = BooleanField().to_python
            values = [clean(v) for v in values]

        query = operator.get_q(model=self._model,
                               field_name=self._field_name,
                               values=values,
                              )

        if operator.exclude:
            query.negate()  # TODO: move more code in operator ??

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
                    '{}.build_daterange_dict(): invalid date range.'.format(cls.__name__)
                )

            range_dict['name'] = date_range
        else:
            if start: range_dict['start'] = date_2_dict(start)
            if end:   range_dict['end']   = date_2_dict(end)

        if not range_dict:
            raise cls.ValueError('date_range or start/end must be given.')

        return range_dict

    def _get_date_range(self):
        "Get a <creme_core.utils.date_range.DateRange> instance from the attributes."
        return date_range_registry.get_range(name=self._range_name,
                                             start=self._start,
                                             end=self._end,
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
                '{}._load_daterange_kwargs() -> invalid data ({} is not a dict)'.format(
                    cls.__name__, data,
                )
            )

        get = data.get
        kwargs = {'date_range': get('name')}

        for key in ('start', 'end'):
            date_kwargs = get(key)
            if date_kwargs:
                if not isinstance(date_kwargs, dict):
                    raise cls.DataError(
                        '{}._load_daterange_kwargs() -> invalid data ({} is not a dict)'.format(
                            cls.__name__, date_kwargs,
                    ))

                try:
                    dt = datetime(**date_kwargs)
                except TypeError as e:
                    raise cls.DataError(
                        '{}._load_daterange_kwargs() -> invalid data for date ({})'.format(
                            cls.__name__, e,
                    ))
                else:
                    kwargs[key] = make_aware_dt(dt)

        return kwargs


class DateRegularFieldConditionHandler(DateFieldHandlerMixin, FilterConditionHandler):
    """Filter entities by using one of their date fields."""
    type_id = 6

    def __init__(self, *, model, field_name, **kwargs):
        FilterConditionHandler.__init__(self, model=model)
        self._field_name = field_name
        DateFieldHandlerMixin.__init__(self, **kwargs)

    @classmethod
    def build(cls, *, model, name, data):
        return cls(
            model=model,
            field_name=name,
            **cls._load_daterange_kwargs(data),  # TODO: test errors (empty, other ?)
        )

    @classmethod
    def build_condition(cls, model, field_name,
                        date_range=None, start=None, end=None,
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
        @param condition_cls: Class of condition.

        If a custom range is used, at least one of the 2 argument "start" & "end"
        must be filled with a date.
        """
        # TODO: factorise
        try:
            finfo = FieldInfo(model, field_name)
        except FieldDoesNotExist as e:
            raise cls.ValueError(str(e)) from e

        if not is_date_field(finfo[-1]):
            raise cls.ValueError(
                '{}.build_condition(): field must be a date field.'.format(cls.__name__)
            )

        return condition_cls(
            model=model,
            type=cls.type_id,
            name=field_name,
            value=condition_cls.encode_value(
                cls._build_daterange_dict(date_range, start, end)
            ),
        )

    @property
    def error(self):
        try:
            finfo = FieldInfo(self._model, self._field_name)
        except FieldDoesNotExist as e:
            return str(e)

        if not is_date_field(finfo[-1]):
            return "'{}' is not a date field".format(self._field_name)

    def get_q(self, user):
        return Q(**self._get_date_range().get_q_dict(field=self._field_name, now=now()))


class BaseCustomFieldConditionHandler(FilterConditionHandler):
    def __init__(self, *, model=None, custom_field, related_name=None):
        """Constructor.

        @param model: Class inheriting <creme_core.models.CremeEntity>
               (ignored if an EntityFilter instance is passed for "custom_field" -- see below).
        @param custom_field: <creme_core.models.CustomField> instance or ID (int).
        @param operator_id: ID of operator
               (see <creme_core.core.entity_filter.operators.OPERATORS>).
        @param related_name: Related name (django's way) corresponding to the
               used CustomField.
        """
        if isinstance(custom_field, CustomField):
            super().__init__(model=custom_field.content_type.model_class())
            self._custom_field_id = custom_field.id
            self._related_name = custom_field.get_value_class().get_related_name()
        else:
            if model is None:
                raise TypeError(
                    'The argument "model" must be passed if a CustomField ID is passed.'
                )
            if related_name is None:
                raise TypeError(
                    'The argument "related_name" must be passed if a CustomField ID is passed.'
                )

            super().__init__(model=model)
            self._custom_field_id = custom_field
            self._related_name = related_name

    @property
    def error(self):
        rname = self._related_name
        if not any(rname == cf_cls.get_related_name() for cf_cls in _TABLES.values()):
            return "related_name '{}' is invalid".format(rname)

    @classmethod
    def query_for_related_conditions(cls, instance):
        return Q(
            type=cls.type_id,
            name=str(instance.id),
        ) if isinstance(instance, CustomField) else Q()


class CustomFieldConditionHandler(OperatorConditionHandlerMixin,
                                  BaseCustomFieldConditionHandler,
                                 ):
    """Filter entities by using one of their CustomFields.
    Note: no date field ; see DateCustomFieldConditionHandler
    """
    type_id = 20
    operators = operators.OPERATORS

    def __init__(self, *, model=None, custom_field, related_name=None, operator_id, values):
        """Constructor.

        @param model: See <BaseCustomFieldConditionHandler>.
        @param custom_field: See <BaseCustomFieldConditionHandler>.
        @param related_name: See <BaseCustomFieldConditionHandler>.
        @param operator_id: ID of operator
               (see <creme_core.core.entity_filter.operators.OPERATORS>).
        @param values: List of values to filter with.
        """
        super().__init__(model=model, custom_field=custom_field, related_name=related_name)
        self._operator_id = operator_id
        self._values = values

    @classmethod
    def build(cls, *, model, name, data):
        try:
            cf_id = int(name)
            kwargs = {
                'operator_id':  int(data['operator']),
                'related_name': data['rname'],  # NB: we could remove it...
                'values':       data['value'],  # TODO: check if it's a list ? check content ?
            }
        except (TypeError, KeyError, ValueError) as e:
            raise cls.DataError(
                '{}.build(): invalid data ({})'.format(cls.__name__, e)
            )

        return cls(model=model, custom_field=cf_id, **kwargs)

    @classmethod
    def build_condition(cls, *, custom_field, operator_id, values, user=None,
                        condition_cls=EntityFilterCondition,
                        efilter_registry=entity_filter_registry,
                       ):
        """Build an (unsaved) EntityFilterCondition.

        @param custom_field: Instance of <creme_core.models.CustomField>.
        @param operator_id: Operator ID ;
               see 'creme_core.core.entity_filter.operators.EQUALS' and friends.
        @param values: List of searched values (logical OR between them).
               Exceptions: - RANGE: 'values' is always a list of 2 elements
                           - ISEMPTY: 'values' is a list containing one boolean.
        @param user: Some fields need a user instance for permission validation.
        @param condition_cls: Class of condition.
        @param efilter_registry: Instance of <_EntityFilterRegistry>.
        """
        if operator_id not in cls.operators:
            raise cls.ValueError(
                '{}.build_condition(): unknown operator: {}'.format(cls.__name__, operator_id)
            )

        if custom_field.field_type == CustomField.DATETIME:
            raise cls.ValueError(
                '{}.build_condition(): does not manage DATE CustomFields'.format(cls.__name__)
            )

        # TODO: A bit ugly way to validate operators, but needed for compatibility.
        if custom_field.field_type == CustomField.BOOL and \
           operator_id not in (operators.EQUALS, operators.EQUALS_NOT, operators.ISEMPTY):
            raise cls.ValueError(
                '{}.build_condition(): BOOL type is only compatible with '
                'EQUALS, EQUALS_NOT and ISEMPTY operators'.format(cls.__name__)
            )

        if not isinstance(values, (list, tuple)):
            raise cls.ValueError(
                '{}.build_condition(): value is not an array'.format(cls.__name__)
            )

        cf_value_class = custom_field.get_value_class()

        try:
            if operator_id == operators.ISEMPTY:
                operator_obj = operators.OPERATORS.get(operator_id)
                value = operator_obj.validate_field_values(
                    field=None, values=values, user=user,
                    efilter_registry=efilter_registry,
                )
            else:
                clean_value = cf_value_class.get_formfield(custom_field, None, user=user).clean

                if custom_field.field_type == CustomField.MULTI_ENUM:
                    value = [str(clean_value([v])[0]) for v in values]
                else:
                    value = [str(clean_value(v)) for v in values]
        except Exception as e:
            raise cls.ValueError(str(e)) from e

        # TODO: migration which replaces single value by arrays of values.
        value = {
            'operator': operator_id,
            'value':    value,
            'rname':    cf_value_class.get_related_name(),
        }

        return condition_cls(
            model=custom_field.content_type.model_class(),
            type=cls.type_id,
            name=str(custom_field.id),
            value=condition_cls.encode_value(value),
        )

    @property
    def error(self):
        return self._check_operator(self._operator_id) or super().error

    def get_q(self, user):
        # NB: Sadly we retrieve the ids of the entity that match with this condition
        #     instead of use a 'JOIN', in order to avoid the interaction between
        #     several conditions on the same type of CustomField (ie: same table).
        operator = operators.OPERATORS[self._operator_id]
        related_name = self._related_name
        fname = '{}__value'.format(related_name)
        values = self._values

        # HACK : compatibility code which converts old filters values into array.
        if not isinstance(values, (list, tuple)):
            values = [values]

        resolve = self.resolve_operand
        resolved_values = [resolve(value, user) for value in values]

        # HACK : compatibility with older format
        if CustomFieldBoolean.get_related_name() == related_name:
            clean_bool = BooleanField().to_python
            resolved_values = [clean_bool(v) for v in resolved_values]

        # TODO: move more code in operator ??
        if isinstance(operator, operators.IsEmptyOperator):
            query = Q(**{'{}__isnull'.format(related_name): resolved_values[0]})
        else:
            query = Q(**{'{}__custom_field'.format(related_name): self._custom_field_id})
            key = operator.key_pattern.format(fname)
            value_q = Q()

            for value in resolved_values:
                value_q |= Q(**{key: value})

            query &= value_q

        if operator.exclude:
            query.negate()  # TODO: move this in operator ??

        return Q(pk__in=self._model
                            ._default_manager
                            .filter(query)
                            .values_list('id', flat=True)
                )


class DateCustomFieldConditionHandler(DateFieldHandlerMixin,
                                      BaseCustomFieldConditionHandler,
                                     ):
    """Filter entities by using one of their date CustomFields."""
    type_id = 21

    def __init__(self, *, model=None, custom_field, related_name=None, **kwargs):
        """Constructor.

        @param model: See <BaseCustomFieldConditionHandler>.
        @param custom_field: See <BaseCustomFieldConditionHandler>.
        @param related_name: See <BaseCustomFieldConditionHandler>.
        @param date_range: See <DateFieldHandlerMixin>.
        @param start: See <DateFieldHandlerMixin>.
        @param end: See <DateFieldHandlerMixin>.
        """
        BaseCustomFieldConditionHandler.__init__(
            self, model=model, custom_field=custom_field, related_name=related_name,
        )
        DateFieldHandlerMixin.__init__(self, **kwargs)

    @classmethod
    def build(cls, *, model, name, data):
        kwargs = cls._load_daterange_kwargs(data)  # Test if it's a dict too
        try:
            cf_id = int(name)
            rname = data['rname']
        except (KeyError, ValueError) as e:
            raise cls.DataError(
                '{}.build(): invalid data ({})'.format(cls.__name__, e)
            )

        return cls(model=model, custom_field=cf_id, related_name=rname, **kwargs)

    @classmethod
    def build_condition(cls, *, custom_field, date_range=None, start=None, end=None,
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
        @param condition_cls: Class of condition.

        If a custom range is used, at least one of the 2 argument "start" & "end"
        must be filled with a date.
        """
        if not custom_field.field_type == CustomField.DATETIME:
            raise cls.ValueError(
                '{}.build_condition(): not a date custom field.'.format(cls.__name__)
            )

        value = cls._build_daterange_dict(date_range, start, end)
        value['rname'] = custom_field.get_value_class().get_related_name()

        return condition_cls(
            model=custom_field.content_type.model_class(),
            type=cls.type_id,
            name=str(custom_field.id),
            value=condition_cls.encode_value(value),
        )

    def get_q(self, user):
        # NB: see CustomFieldConditionHandler.get_q() remark
        related_name = self._related_name
        fname = '{}__value'.format(related_name)

        q_dict = self._get_date_range().get_q_dict(field=fname, now=now())
        q_dict['{}__custom_field'.format(related_name)] = self._custom_field_id

        return Q(pk__in=self._model
                            ._default_manager
                            .filter(**q_dict)
                            .values_list('id', flat=True)
                )


class BaseRelationConditionHandler(FilterConditionHandler):
    @classmethod
    def query_for_related_conditions(cls, instance):
        return Q(
            type=cls.type_id,
            name=instance.id,
        ) if isinstance(instance, RelationType) else Q()


class RelationConditionHandler(BaseRelationConditionHandler):
    """Filter entities which are have (or have not) certain Relations."""
    type_id = 10

    def __init__(self, *, model, rtype, exclude=False, ctype=None, entity=None):
        super().__init__(model=model)
        self._rtype_id = rtype.id if isinstance(rtype, RelationType) else rtype
        self._exclude = exclude

        if isinstance(entity, CremeEntity):
            self._entity_id = entity.id
            self._ct_id = None
        else:
            self._entity_id = entity
            self._ct_id = ctype.id if isinstance(ctype, ContentType) else ctype

    @classmethod
    def build(cls, *, model, name, data):
        try:
            has = data['has']

            ct_id = data.get('ct_id')
            if ct_id is not None:
                ct_id = int(ct_id)

            entity_id = data.get('entity_id')
            if entity_id is not None:
                entity_id = int(entity_id)
        except (TypeError, KeyError, ValueError) as e:
            raise cls.DataError(
                '{}.build(): invalid data ({})'.format(cls.__name__, e)
            )

        if not isinstance(has, bool):
            raise cls.DataError(
                '{}.build(): "has" is not a boolean'.format(cls.__name__)
            )

        return cls(
            model=model,
            rtype=name,
            exclude=not has,
            ctype=ct_id,
            entity=entity_id,
        )

    @classmethod
    def build_condition(cls, *, model, rtype, has=True, ct=None, entity=None,
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
        @param condition_cls: Class of condition.
        """
        value = {'has': bool(has)}

        if entity:
            value['entity_id'] = entity.id
        elif ct:
            value['ct_id'] = ct.id

        return condition_cls(
            model=model,
            type=cls.type_id,
            name=rtype.id,
            value=condition_cls.encode_value(value),
        )

    # TODO: use a filter "relations__*" when there is only one condition on Relations ??
    def get_q(self, user):
        kwargs = {'type': self._rtype_id}

        if self._entity_id:
            kwargs['object_entity'] = self._entity_id
        elif self._ct_id:
            kwargs['object_entity__entity_type'] = self._ct_id

        query = Q(pk__in=Relation.objects
                                 .filter(**kwargs)
                                 .values_list('subject_entity_id', flat=True)
                 )

        if self._exclude:
            query.negate()

        return query


class RelationSubFilterConditionHandler(BaseRelationConditionHandler):
    """Filter entities which are have (or have not) certain Relations.
    with entities filtered by a a sub EntityFilter.
    """
    type_id = 11

    def __init__(self, *, model, rtype, subfilter, exclude=False):
        """Constructor.

        @param model: Class inheriting <creme_core.models.CremeEntity>.
        @param rtype: <creme_core.models.RelationType> instance or ID (string).
        @param subfilter: <creme_core.models.EntityFilter> instance or ID (string).
        @param exclude: Boolean ; the retrieved Relations have to be
               included (True) or excluded (False).
        """
        super().__init__(model=model)
        if isinstance(subfilter, EntityFilter):
            self._subfilter_id = subfilter.id
            self._subfilter    = subfilter  # TODO: copy ?
        else:
            self._subfilter_id = subfilter

        self._rtype_id = rtype.id if isinstance(rtype, RelationType) else rtype
        self._exclude = exclude

    @classmethod
    def build(cls, *, model, name, data):
        try:
            filter_id = data['filter_id']
            has = data['has']
        except (TypeError, KeyError) as e:
            raise cls.DataError(
                '{}.build(): invalid data ({})'.format(cls.__name__, e)
            )

        if not isinstance(has, bool):
            raise cls.DataError(
                '{}.build(): "has" is not a boolean'.format(cls.__name__)
            )

        return cls(model=model, rtype=name, subfilter=filter_id, exclude=not has)

    @classmethod
    def build_condition(cls, *, model, rtype, subfilter, has=True,
                        condition_cls=EntityFilterCondition
                       ):
        """Build an (unsaved) EntityFilterCondition.

        @param model: Class inheriting <creme_core.models.CremeEntity>.
        @param rtype: Instance of <creme_core.models.RelationType>.
        @param subfilter: Instance of <creme_core.models.models.EntityFilter>.
        @param has: Boolean indicating if the filtered entities have (<True>)
               or have not (<False>) the retrieved Relations.
        @param condition_cls: Class of condition.
        """
        assert isinstance(subfilter, EntityFilter)
        has = bool(has)

        return condition_cls(
            model=model,
            type=cls.type_id,
            name=rtype.id,
            value=condition_cls.encode_value(
                {'has': has, 'filter_id': subfilter.id}
            ),
            # NB: avoid a query to retrieve again the sub-filter (in forms).
            handler=cls(model=model, rtype=rtype, subfilter=subfilter, exclude=not has),
        )

    @property
    def error(self):
        # TODO: error if relation type not found ?
        if self.subfilter is False:
            return "'{}' is not a valid filter ID".format(self.subfilter_id)

    # TODO: use a filter "relations__*" when there is only one condition on Relations ??
    def get_q(self, user):
        subfilter = self.subfilter
        filtered = subfilter.filter(subfilter.entity_type.model_class().objects.all()) \
                            .values_list('id', flat=True)

        query = Q(pk__in=Relation.objects
                                 .filter(type=self._rtype_id, object_entity__in=filtered)
                                 .values_list('subject_entity_id', flat=True)
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


class PropertyConditionHandler(FilterConditionHandler):
    """Filter entities which are have (or have not) certain CremeProperties."""
    type_id = 15

    def __init__(self, *, model, ptype, exclude=False):
        """Constructor.

        @param model: Class inheriting <creme_core.models.CremeEntity>.
        @param ptype: <creme_core.models.CremePropertyType> instance or ID (string).
        @param exclude: Boolean ; the retrieved CremeProperties have to be
               included (True) or excluded (False).
        """
        super().__init__(model=model)
        self._ptype_id = ptype.id if isinstance(ptype, CremePropertyType) else ptype
        self._exclude = exclude

    @classmethod
    def build(cls, *, model, name, data):
        if not isinstance(data, bool):
            raise cls.DataError(
                '{}.build(): invalid data (not boolean)'.format(cls.__name__)
            )

        return cls(model=model, ptype=name, exclude=not data)

    @classmethod
    def build_condition(cls, *, model, ptype, has=True, condition_cls=EntityFilterCondition):
        """Build an (unsaved) EntityFilterCondition.

        @param model: Class inheriting <creme_core.models.CremeEntity>.
        @param ptype: Instance of <creme_core.models.CremePropertyType>.
        @param has: Boolean indicating if the filtered entities have (<True>)
               or have not (<False>) the retrieved CremeProperties.
        @param condition_cls: Class of condition.
        """
        return condition_cls(
            model=model,
            type=cls.type_id,
            name=ptype.id,
            value=condition_cls.encode_value(bool(has)),
        )

    # TODO: see remark on RelationConditionHandler._get_q()
    def get_q(self, user):
        query = Q(pk__in=CremeProperty.objects
                                      .filter(type=self._ptype_id)
                                      .values_list('creme_entity_id', flat=True)
                 )

        if self._exclude:  # Is a boolean indicating if got or has not got the property type
            query.negate()

        return query

    @classmethod
    def query_for_related_conditions(cls, instance):
        return Q(
            type=cls.type_id,
            name=instance.id,
        ) if isinstance(instance, CremePropertyType) else Q()
