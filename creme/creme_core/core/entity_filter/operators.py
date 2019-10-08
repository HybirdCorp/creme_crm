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

from functools import partial
import operator

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.query_utils import Q
from django.utils.translation import gettext_lazy as _, gettext

# from creme.creme_core.models import EntityFilter
from creme.creme_core.utils.db import is_db_case_sensitive
from creme.creme_core.utils.meta import FieldInfo

from . import entity_filter_registry

# IDs
EQUALS          =  1
IEQUALS         =  2
EQUALS_NOT      =  3
IEQUALS_NOT     =  4
CONTAINS        =  5
ICONTAINS       =  6
CONTAINS_NOT    =  7
ICONTAINS_NOT   =  8
GT              =  9
GTE             = 10
LT              = 11
LTE             = 12
STARTSWITH      = 13
ISTARTSWITH     = 14
STARTSWITH_NOT  = 15
ISTARTSWITH_NOT = 16
ENDSWITH        = 17
IENDSWITH       = 18
ENDSWITH_NOT    = 19
IENDSWITH_NOT   = 20
ISEMPTY         = 21
RANGE           = 22

FIELDTYPES_ALL = {
    'string',
    'enum', 'enum__null',
    'number', 'number__null',
    'date', 'date__null',
    'boolean', 'boolean__null',
    'fk', 'fk__null',
    'user', 'user__null',
}
FIELDTYPES_ORDERABLE = {
    'number', 'number__null',
    'date', 'date__null',
}
FIELDTYPES_RELATED = {
    'fk', 'fk__null',
    'enum', 'enum__null',
}
FIELDTYPES_NULLABLE = {
    'string',
    'fk__null',
    'user__null',
    'enum__null',
    'boolean__null',
}
FIELDTYPES_STRING = {
    'string',
}


# class _ConditionOperator:
class ConditionOperator:
    """Some child classes of
    <creme_core.core.entity_filter.condition_handler.FilterConditionHandler> can
    use different operators (eg: "equal", greater than", "contains"...) when
    performing the SQL query. These operator are modeled with <ConditionOperator>.

    The main feature is the method <get_q()> with provides a <Q> instance to
    perform the wanted SQL query.
    """
    # __slots__ = ('name', '_accept_subpart', '_exclude', '_key_pattern', '_allowed_fieldtypes')

    # Fields for which the subpart of a valid value is not valid
    _NO_SUBPART_VALIDATION_FIELDS = {
        models.EmailField,
        models.IPAddressField,
    }

    # Integer ID (see EQUALS & its friends) used for registration.
    type_id = None

    # Used in forms to configure the condition (see creme_core/forms/entity_filter.py)
    verbose_name = ''

    # Sequence of strings used by the form fields/widgets to know which
    # operators to propose for a given model-field (see creme_core/forms/entity_filter.py).
    allowed_fieldtypes = ()

    # Boolean ;  <True> means that the operand given by the user should not be
    # validated because sub-part of a valid input must be accepted.
    #   Eg: we want to search in the values of an EmailField with a string
    #       which is not a complete (& so, valid) e-mail address.
    accept_subpart = True

    # Format string used by <description()>.
    description_pattern = '«{field}» OP {values}'

    # Format string used to build the Q instance ("{}" is interpolated with the field name).
    key_pattern = '{}__exact'
    # (Boolean) Are the filtered objects included or excluded?
    exclude = False

    # def __init__(self, name, key_pattern, exclude=False, accept_subpart=True, allowed_fieldtypes=None):
    #     self._key_pattern    = key_pattern
    #     self._exclude        = exclude
    #     self._accept_subpart = accept_subpart
    #     self._description_pattern = description_pattern
    #     self.name = name
    #     self._allowed_fieldtypes = allowed_fieldtypes or ()

    def _accept_value(self, *, field_value, value):
        raise NotImplementedError

    def accept(self, *, field_value, values):
        """Check if when applying N times the operator to a value
        (eg: corresponding to a field of an instance) and a value from a list
        of N values, one result at least is True.

        Eg: for an "EQUAL" operator:
         >> accept(field_value=2, values=[1, 2]) would return <True>.
         >> accept(field_value=2, values=[1, 3]) would return <False>.
        """
        accept_value = partial(self._accept_value, field_value=field_value)
        accepted = any(accept_value(value=value) for value in values)

        return not accepted if self.exclude else accepted

    # @property
    # def allowed_fieldtypes(self):
    #     return self._allowed_fieldtypes

    def description(self, *, field_vname, values):
        """Description of the operation for human.

        @param field_vname: Verbose name of the field (regular or custom).
        @param values: List of operands.
        @return: A localized string.
        """
        if values:
            return self.description_pattern.format(
                field=field_vname,
                values=self._enumeration(values),
            )

        return '??'

    @staticmethod
    def _enumeration(values):
        value_format = gettext('«{enum_value}»').format
        first_part = ', '.join(value_format(enum_value=v) for v in values[:-1])

        return gettext('{first} or {last}').format(
                    first=first_part,
                    last=value_format(enum_value=values[-1]),
               ) \
               if first_part else \
               value_format(enum_value=values[-1])

    # @property
    # def exclude(self):
    #     return self._exclude

    # @property
    # def key_pattern(self):
    #     return self._key_pattern

    # @property
    # def accept_subpart(self):
    #     return self._accept_subpart

    def __str__(self):
        return str(self.verbose_name)

    # def get_q(self, efcondition, values):
    def get_q(self, *, model, field_name, values):
        """Get the query to filter instance.

        @param model: Class inheriting <django.db.model>.
        @param field_name: Name of a model-field (of 'model').
        @param values: Sequence of values the field can have.
        @return: An instance of <django.db.models.Q>.
        """
        # key = self.key_pattern.format(efcondition.name)
        key = self.key_pattern.format(field_name)
        query = Q()

        for value in values:
            query |= Q(**{key: value})

        return query

    # def validate_field_values(self, field, values, user=None):
    def validate_field_values(self, *, field, values, user=None,
                              efilter_registry=entity_filter_registry):
        """Raises a ValidationError to notify of a problem with 'values'.
        @param field: Model field.
        @param values: Sequence of POSTed values to validate.
        @param user: Instance of <django.contrib.auth.get_user_model()>. Logged user.
        @param efilter_registry: Instance of <_EntityFilterRegistry>.
        @raise: ValidationError.
        """
        # from . import entity_filter_registry

        # if not field.__class__ in self._NO_SUBPART_VALIDATION_FIELDS or not self.accept_subpart:
        if type(field) not in self._NO_SUBPART_VALIDATION_FIELDS or not self.accept_subpart:
            formfield = field.formfield()
            formfield.user = user

            clean = formfield.clean
            # variable = None
            is_multiple = isinstance(field, models.ManyToManyField)

            for value in values:
                # variable = EntityFilter.get_variable(value)
                operand = efilter_registry.get_operand(type_id=value, user=user)

                if operand is not None:
                    operand.validate(field=field, value=value)
                else:
                    # TODO: validate all values at once for ManyToManyField ?
                    clean([value] if is_multiple else value)

        return values


class EqualsOperator(ConditionOperator):
    type_id = EQUALS
    verbose_name = _('Equals')
    allowed_fieldtypes = FIELDTYPES_ALL
    accept_subpart = False
    description_pattern = _('«{field}» is {values}')
    key_pattern = '{}__exact'  # NB: have not real meaning here

    def _accept_single_value(self, *, field_value, value):
        if is_db_case_sensitive():
            v1 = field_value
            v2 = value
        else:
            v1 = field_value.lower() if isinstance(field_value, str) else field_value
            v2 = value.lower()       if isinstance(value, str) else value

        return v1 == v2

    def _accept_value(self, *, field_value, value):
        if isinstance(value, (list, tuple)):
            return any(
                self._accept_single_value(field_value=field_value, value=v)
                    for v in value
            )

        return self._accept_single_value(field_value=field_value, value=value)

    # def get_q(self, efcondition, values):
    #     name = efcondition.name
    #     query = Q()
    #
    #     for value in values:
    #         if isinstance(value, (list, tuple)):
    #             q = Q(**{'{}__in'.format(name): value})
    #         else:
    #             q = Q(**{self.key_pattern.format(name): value})
    #
    #         query |= q
    #
    #     return query
    def get_q(self, *, model, field_name, values):
        if not values:
            q = Q()
        elif len(values) == 1:
            q = Q(**{self.key_pattern.format(field_name): values[0]})
        else:
            q = Q(**{'{}__in'.format(field_name): values})

        return q


class EqualsNotOperator(EqualsOperator):
    type_id = EQUALS_NOT
    verbose_name = _('Does not equal')
    description_pattern = _('«{field}» is not {values}')
    exclude = True


# TODO: <accept_subpart = False> when it's integer ?
# TODO: several values are stupid here
class NumericOperatorBase(ConditionOperator):
    allowed_fieldtypes = FIELDTYPES_ORDERABLE
    operator = lambda a, b: False

    def _accept_value(self, *, field_value, value):
        return False if field_value is None else self.operator(field_value, value)


class GTOperator(NumericOperatorBase):
    type_id = GT
    verbose_name = _('>')
    description_pattern = _('«{field}» is greater than {values}')
    key_pattern = '{}__gt'
    operator = operator.gt


class GTEOperator(NumericOperatorBase):
    type_id = GTE
    verbose_name = _('≥')
    description_pattern = _('«{field}» is greater than or equal to {values}')
    key_pattern = '{}__gte'
    operator = operator.ge


class LTOperator(NumericOperatorBase):
    type_id = LT
    verbose_name = _('<')
    description_pattern = _('«{field}» is less than {values}')
    key_pattern = '{}__lt'
    operator = operator.lt


class LTEOperator(NumericOperatorBase):
    type_id = LTE
    verbose_name = _('≤')
    description_pattern = _('«{field}» is less than or equal to {values}')
    key_pattern = '{}__lte'
    operator = operator.le


class StringOperatorBase(ConditionOperator):
    allowed_fieldtypes = FIELDTYPES_STRING
    case_sensitive = True

    def _accept_string(self, *, field_value, value):
        raise NotImplementedError

    def _accept_value(self, *, field_value, value):
        if field_value is None:
            return False

        # TODO: local cache (in self) for <is_db_case_sensitive()> ??
        if not self.case_sensitive or not is_db_case_sensitive():
            value = value.lower()
            field_value = field_value.lower()  # TODO: field_value.lower() once ??

        return self._accept_string(field_value=field_value, value=value)


class IEqualsOperator(StringOperatorBase):
    type_id = IEQUALS
    verbose_name = _('Equals (case insensitive)')
    accept_subpart = False
    description_pattern = _('«{field}» is equal to {values} (case insensitive)')
    key_pattern = '{}__iexact'
    case_sensitive = False

    def _accept_string(self, *, field_value, value):
        return value == field_value


class IEqualsNotOperator(IEqualsOperator):
    type_id = IEQUALS_NOT
    verbose_name = _('Does not equal (case insensitive)')
    description_pattern = _('«{field}» is different from {values} (case insensitive)')
    exclude = True


class ContainsOperator(StringOperatorBase):
    type_id = CONTAINS
    verbose_name = _('Contains')
    description_pattern = _('«{field}» contains {values}')
    key_pattern = '{}__contains'

    def _accept_string(self, *, field_value, value):
        return value in field_value


class ContainsNotOperator(ContainsOperator):
    type_id = CONTAINS_NOT
    verbose_name = _('Does not contain')
    description_pattern = _('«{field}» does not contain {values}')
    exclude = True


class IContainsOperator(ContainsOperator):
    type_id = ICONTAINS
    verbose_name = _('Contains (case insensitive)')
    description_pattern = _('«{field}» contains {values} (case insensitive)')
    key_pattern = '{}__icontains'
    case_sensitive = False


class IContainsNotOperator(IContainsOperator):
    type_id = ICONTAINS_NOT
    verbose_name = _('Does not contain (case insensitive)')
    description_pattern = _('«{field}» does not contain {values} (case insensitive)')
    exclude = True


class StartsWithOperator(StringOperatorBase):
    type_id = STARTSWITH
    verbose_name = _('Starts with')
    description_pattern = _('«{field}» starts with {values}')
    key_pattern = '{}__startswith'

    def _accept_string(self, *, field_value, value):
        return field_value.startswith(value)


class StartswithNotOperator(StartsWithOperator):
    type_id = STARTSWITH_NOT
    verbose_name = _('Does not start with')
    description_pattern = _('«{field}» does not start with {values}')
    exclude = True


class IStartsWithOperator(StartsWithOperator):
    type_id = ISTARTSWITH
    verbose_name = _('Starts with (case insensitive)')
    description_pattern = _('«{field}» starts with {values} (case insensitive)')
    key_pattern = '{}__istartswith'
    case_sensitive = False


class IStartswithNotOperator(IStartsWithOperator):
    type_id = ISTARTSWITH_NOT
    verbose_name = _('Does not start with (case insensitive)')
    description_pattern = _('«{field}» does not start with {values} (case insensitive)')
    exclude = True


class EndsWithOperator(StringOperatorBase):
    type_id = ENDSWITH
    verbose_name = _('Ends with')
    description_pattern = _('«{field}» ends with {values}')
    key_pattern = '{}__endswith'

    def _accept_string(self, *, field_value, value):
        return field_value.endswith(value)


class EndsWithNotOperator(EndsWithOperator):
    type_id = ENDSWITH_NOT
    verbose_name = _('Does not end with')
    description_pattern = _('«{field}» does not end with {values}')
    exclude = True


class IEndsWithOperator(EndsWithOperator):
    type_id = IENDSWITH
    verbose_name = _('Ends with (case insensitive)')
    description_pattern = _('«{field}» ends with {values} (case insensitive)')
    key_pattern = '{}__iendswith'
    case_sensitive = False


class IEndsWithNotOperator(IEndsWithOperator):
    type_id = IENDSWITH_NOT
    verbose_name = _('Does not end with (case insensitive)')
    description_pattern = _('«{field}» does not end with {values} (case insensitive)')
    exclude = True


# class _ConditionBooleanOperator(_ConditionOperator):
class BooleanOperatorBase(ConditionOperator):
    # def validate_field_values(self, field, values, user=None):
    def validate_field_values(self, *, field, values, user=None,
                              efilter_registry=entity_filter_registry):
        if len(values) != 1 or not isinstance(values[0], bool):
            # raise ValueError(
            raise ValidationError(
                'A list with one bool is expected for boolean operator {}'.format(self.verbose_name)
            )

        return values


# class _IsEmptyOperator(_ConditionBooleanOperator):
class IsEmptyOperator(BooleanOperatorBase):
    type_id = ISEMPTY
    verbose_name = _('Is empty')
    allowed_fieldtypes = FIELDTYPES_NULLABLE
    accept_subpart = False
    description_patterns = {
        True:  _('«{field}» is empty'),
        False: _('«{field}» is not empty'),
    }
    key_pattern = '{}__isnull'  # NB: have not real meaning here

    # def __init__(self, name, exclude=False, **kwargs):
    #     super().__init__(name, key_pattern='{}__isnull',
    #                      exclude=exclude, accept_subpart=False,
    #                      **kwargs
    #                     )

    def _accept_value(self, *, field_value, value):
        # NB: we should only use with strings
        filled = bool(field_value)
        return not filled if value else filled

    def description(self, *, field_vname, values):
        if values:
            return self.description_patterns[bool(values[0])].format(field=field_vname)

        return super().description(field_vname=field_vname, values=values)

    # def get_q(self, efcondition, values):
    def get_q(self, *, model, field_name, values):
        # field_name = efcondition.name

        # As default, set isnull operator (always true, negate is done later)
        # query = Q(**{self.key_pattern % field_name: True})
        query = Q(**{self.key_pattern.format(field_name): True})

        # Add filter for text fields, "isEmpty" should mean null or empty string
        # finfo = FieldInfo(efcondition.filter.entity_type.model_class(), field_name)
        finfo = FieldInfo(model, field_name)  # TODO: what about CustomField ?!
        if isinstance(finfo[-1], (models.CharField, models.TextField)):
            query |= Q(**{field_name: ''})

        # Negate filter on false value
        if not values[0]:
            query.negate()

        return query


# class _RangeOperator(_ConditionOperator):
class RangeOperator(ConditionOperator):
    type_id = RANGE
    verbose_name = _('Range')
    allowed_fieldtypes = ('number', 'date')
    description_pattern = _('«{field}» is between «{start}» and «{end}»')
    key_pattern = '{}__range'

    def _accept_value(self, *, field_value, value):
        return False if field_value is None else \
               value[0] <= field_value <= value[1]

    def description(self, *, field_vname, values):
        return self.description_pattern.format(
                field=field_vname,
                start=values[0],
                end=values[1],
            ) if len(values) == 2 else \
            super().description(field_vname=field_vname, values=None)

    # def validate_field_values(self, field, values, user=None):
    def validate_field_values(self, *, field, values, user=None,
                              efilter_registry=entity_filter_registry):
        if len(values) != 2:
            # raise ValueError(
            raise ValidationError(
                'A list with 2 elements is expected for condition {}'.format(self.verbose_name)
            )

        return [super().validate_field_values(field=field, values=values)]


# _OPERATOR_MAP = {
#     EQUALS:          _ConditionOperator(_(u'Equals'),                                 '{}__exact',
#                                         accept_subpart=False, allowed_fieldtypes=_FIELDTYPES_ALL),
#     IEQUALS:         _ConditionOperator(_(u'Equals (case insensitive)'),              '{}__iexact',
#                                         accept_subpart=False, allowed_fieldtypes=('string',)),
#     EQUALS_NOT:      _ConditionOperator(_(u'Does not equal'),                         '{}__exact',
#                                         exclude=True, accept_subpart=False, allowed_fieldtypes=_FIELDTYPES_ALL),
#     IEQUALS_NOT:     _ConditionOperator(_(u'Does not equal (case insensitive)'),      '{}__iexact',
#                                         exclude=True, accept_subpart=False, allowed_fieldtypes=('string',)),
#     CONTAINS:        _ConditionOperator(_(u'Contains'),                               '{}__contains', allowed_fieldtypes=('string',)),
#     ICONTAINS:       _ConditionOperator(_(u'Contains (case insensitive)'),            '{}__icontains', allowed_fieldtypes=('string',)),
#     CONTAINS_NOT:    _ConditionOperator(_(u'Does not contain'),                       '{}__contains', exclude=True, allowed_fieldtypes=('string',)),
#     ICONTAINS_NOT:   _ConditionOperator(_(u'Does not contain (case insensitive)'),    '{}__icontains', exclude=True, allowed_fieldtypes=('string',)),
#     GT:              _ConditionOperator(_(u'>'),                                      '{}__gt', allowed_fieldtypes=_FIELDTYPES_ORDERABLE),
#     GTE:             _ConditionOperator(_(u'>='),                                     '{}__gte', allowed_fieldtypes=_FIELDTYPES_ORDERABLE),
#     LT:              _ConditionOperator(_(u'<'),                                      '{}__lt', allowed_fieldtypes=_FIELDTYPES_ORDERABLE),
#     LTE:             _ConditionOperator(_(u'<='),                                     '{}__lte', allowed_fieldtypes=_FIELDTYPES_ORDERABLE),
#     STARTSWITH:      _ConditionOperator(_(u'Starts with'),                            '{}__startswith', allowed_fieldtypes=('string',)),
#     ISTARTSWITH:     _ConditionOperator(_(u'Starts with (case insensitive)'),         '{}__istartswith', allowed_fieldtypes=('string',)),
#     STARTSWITH_NOT:  _ConditionOperator(_(u'Does not start with'),                    '{}__startswith', exclude=True, allowed_fieldtypes=('string',)),
#     ISTARTSWITH_NOT: _ConditionOperator(_(u'Does not start with (case insensitive)'), '{}__istartswith', exclude=True, allowed_fieldtypes=('string',)),
#     ENDSWITH:        _ConditionOperator(_(u'Ends with'),                              '{}__endswith', allowed_fieldtypes=('string',)),
#     IENDSWITH:       _ConditionOperator(_(u'Ends with (case insensitive)'),           '{}__iendswith', allowed_fieldtypes=('string',)),
#     ENDSWITH_NOT:    _ConditionOperator(_(u'Does not end with'),                      '{}__endswith', exclude=True, allowed_fieldtypes=('string',)),
#     IENDSWITH_NOT:   _ConditionOperator(_(u'Does not end with (case insensitive)'),   '{}__iendswith', exclude=True, allowed_fieldtypes=('string',)),
#     ISEMPTY:         _IsEmptyOperator(_(u'Is empty'), allowed_fieldtypes=_FIELDTYPES_NULLABLE),
#     RANGE:           _RangeOperator(_(u'Range')),
# }
