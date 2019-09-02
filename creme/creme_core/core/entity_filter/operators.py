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

from django.db import models
from django.db.models.query_utils import Q
from django.utils.translation import gettext_lazy as _, gettext

# from creme.creme_core.models import EntityFilter
from creme.creme_core.utils.meta import FieldInfo

from . import entity_filter_registry

# TODO: register the Operators in <entity_filter_registry>


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

    def __init__(self, name, key_pattern,
                 exclude=False, accept_subpart=True, allowed_fieldtypes=None,
                 description_pattern=None,
                ):
        """Constructor.

        @param name: Verbose name (ie: for human) of the operator.
               Used in forms to configure the condition (see
               creme_core/forms/entity_filter.py)
        @param key_pattern: Format string used to build the Q instance
               ("{}" is interpolated with the field name).
        @param exclude: (Boolean) Are the filtered objects included or excluded?
        @param accept_subpart: <True> means that the operand given by the user
               should not be validated because sub-part of a valid input must
               be accepted. Eg: we want to search in the values of an EmailField
               with a string which is not a complete (& so, valid) e-mail address.
        @param allowed_fieldtypes: Sequence of strings used by the form fields/widgets
               to know which operators to propose for a given model-field
               (see creme_core/forms/entity_filter.py).
        @param description_pattern: Format string used by <description()>
               (format variable are "{field}" & "{values}").
        """
        self._key_pattern    = key_pattern
        self._exclude        = exclude
        self._accept_subpart = accept_subpart
        self._description_pattern = description_pattern
        self.name            = name

        # Needed by JavaScript widget to filter operators for each field type
        self._allowed_fieldtypes = allowed_fieldtypes or ()  # TODO: copy ?

    @property
    def allowed_fieldtypes(self):
        return self._allowed_fieldtypes

    @property
    def description_pattern(self):
        return self._description_pattern

    def description(self, *, field_vname, values):
        """Description of the operation for human.

        @param field_vname: Verbose name of the field (regular or custom).
        @param values: List of operands.
        @return: A localized string.
        """
        pattern = self.description_pattern

        if values and pattern:
            return pattern.format(
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

    @property
    def exclude(self):
        return self._exclude

    @property
    def key_pattern(self):
        return self._key_pattern

    @property
    def accept_subpart(self):
        return self._accept_subpart

    def __str__(self):
        return str(self.name)

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
                operand = entity_filter_registry.get_operand(type_id=value, user=user)

                if operand is not None:
                    operand.validate(field=field, value=value)
                else:
                    clean([value] if is_multiple else value)

        return values


class EqualsOperator(ConditionOperator):
    # NB: True == exclude
    DESCRIPTION_PATTERNS = {
        False: _('«{field}» is {values}'),
        True:  _('«{field}» is not {values}'),
    }

    # def __init__(self, name, **kwargs):
    def __init__(self, name, exclude=False):
        super().__init__(name,
                         key_pattern='{}__exact',  # NB: have not real meaning here
                         accept_subpart=False,
                         allowed_fieldtypes=FIELDTYPES_ALL,
                         exclude=exclude,
                         # **kwargs
                        )

    @property
    def description_pattern(self):
        return self.DESCRIPTION_PATTERNS[self._exclude]

    # def get_q(self, efcondition, values):
    def get_q(self, *, model, field_name, values):
        # name = efcondition.name
        query = Q()

        for value in values:
            if isinstance(value, (list, tuple)):
                # q = Q(**{'{}__in'.format(name): value})
                q = Q(**{'{}__in'.format(field_name): value})
            else:
                # q = Q(**{self.key_pattern.format(name): value})
                q = Q(**{self.key_pattern.format(field_name): value})

            query |= q

        return query


# class _ConditionBooleanOperator(_ConditionOperator):
class BooleanOperator(ConditionOperator):
    # def validate_field_values(self, field, values, user=None):
    def validate_field_values(self, *, field, values, user=None,
                              efilter_registry=entity_filter_registry):
        if len(values) != 1 or not isinstance(values[0], bool):
            raise ValueError(
                'A list with one bool is expected for boolean operator {}'.format(self.name)
            )

        return values


# class _IsEmptyOperator(_ConditionBooleanOperator):
class IsEmptyOperator(BooleanOperator):
    DESCRIPTION_PATTERNS = {
        True:  _('«{field}» is empty'),
        False: _('«{field}» is not empty'),
    }

    # def __init__(self, name, exclude=False, **kwargs):
    def __init__(self, name, exclude=False):
        super().__init__(name,
                         key_pattern='{}__isnull',  # NB: have not real meaning here
                         exclude=exclude, accept_subpart=False,
                         allowed_fieldtypes=FIELDTYPES_NULLABLE,
                        )

    def description(self, *, field_vname, values):
        if values:
            return self.DESCRIPTION_PATTERNS[bool(values[0])].format(field=field_vname)

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
    DESCRIPTION_PATTERN = _('«{field}» is between «{start}» and «{end}»')

    def __init__(self, name):
        super().__init__(name, '{}__range', allowed_fieldtypes=('number', 'date'))

    def description(self, *, field_vname, values):
        return self.DESCRIPTION_PATTERN.format(
                field=field_vname,
                start=values[0],
                end=values[1],
            ) if len(values) == 2 else \
            super().description(field_vname=field_vname, values=values)

    # def validate_field_values(self, field, values, user=None):
    def validate_field_values(self, *, field, values, user=None,
                              efilter_registry=entity_filter_registry):
        if len(values) != 2:
            raise ValueError(
                'A list with 2 elements is expected for condition {}'.format(self.name)
            )

        return [super().validate_field_values(field=field, values=values)]


OPERATORS = {
    # EQUALS:     EqualsOperator(_('Equals'), allowed_fieldtypes=FIELDTYPES_ALL),
    EQUALS:     EqualsOperator(_('Equals')),
    # EQUALS_NOT: EqualsOperator(_('Equals'), allowed_fieldtypes=FIELDTYPES_ALL, exclude=True),
    EQUALS_NOT: EqualsOperator(_('Equals'), exclude=True),

    # TODO: <accept_subpart = False> when it's integer ?
    # TODO: several values are stupid here
    GT:  ConditionOperator(_('>'),  '{}__gt',  allowed_fieldtypes=FIELDTYPES_ORDERABLE,
                           description_pattern=_('«{field}» is greater than {values}'),
                          ),
    # GTE: ConditionOperator(_('>='), '{}__gte', allowed_fieldtypes=FIELDTYPES_ORDERABLE),
    GTE: ConditionOperator(_('≥'), '{}__gte', allowed_fieldtypes=FIELDTYPES_ORDERABLE,
                           description_pattern=_('«{field}» is greater or equal to {values}'),
                          ),
    LT:  ConditionOperator(_('<'),  '{}__lt',  allowed_fieldtypes=FIELDTYPES_ORDERABLE,
                           description_pattern=_('«{field}» is lesser than {values}'),
                          ),
    # LTE: ConditionOperator(_('<='), '{}__lte', allowed_fieldtypes=FIELDTYPES_ORDERABLE),
    LTE: ConditionOperator(_('≤'), '{}__lte', allowed_fieldtypes=FIELDTYPES_ORDERABLE,
                           description_pattern=_('«{field}» is lesser or equal to {values}'),
                          ),

    IEQUALS:         ConditionOperator(_('Equals (case insensitive)'),              '{}__iexact',      allowed_fieldtypes=FIELDTYPES_STRING,               accept_subpart=False,
                                       description_pattern=_('«{field}» is equal to {values} (case insensitive)'),
                                      ),
    IEQUALS_NOT:     ConditionOperator(_('Does not equal (case insensitive)'),      '{}__iexact',      allowed_fieldtypes=FIELDTYPES_STRING, exclude=True, accept_subpart=False,
                                       description_pattern=_('«{field}» is different from {values} (case insensitive)'),
                                      ),
    CONTAINS:        ConditionOperator(_('Contains'),                               '{}__contains',    allowed_fieldtypes=FIELDTYPES_STRING,
                                       description_pattern=_('«{field}» contains {values}'),
                                      ),
    CONTAINS_NOT:    ConditionOperator(_('Does not contain'),                       '{}__contains',    allowed_fieldtypes=FIELDTYPES_STRING, exclude=True,
                                       description_pattern=_('«{field}» does not contain {values}'),
                                      ),
    ICONTAINS:       ConditionOperator(_('Contains (case insensitive)'),            '{}__icontains',   allowed_fieldtypes=FIELDTYPES_STRING,
                                       description_pattern=_('«{field}» contains {values} (case insensitive)'),
                                      ),
    ICONTAINS_NOT:   ConditionOperator(_('Does not contain (case insensitive)'),    '{}__icontains',   allowed_fieldtypes=FIELDTYPES_STRING, exclude=True,
                                       description_pattern=_('«{field}» does not contain {values} (case insensitive)'),
                                      ),
    STARTSWITH:      ConditionOperator(_('Starts with'),                            '{}__startswith',  allowed_fieldtypes=FIELDTYPES_STRING,
                                       description_pattern=_('«{field}» starts with {values}'),
                                      ),
    STARTSWITH_NOT:  ConditionOperator(_('Does not start with'),                    '{}__startswith',  allowed_fieldtypes=FIELDTYPES_STRING, exclude=True,
                                       description_pattern=_('«{field}» does not start with {values}'),
                                      ),
    ISTARTSWITH:     ConditionOperator(_('Starts with (case insensitive)'),         '{}__istartswith', allowed_fieldtypes=FIELDTYPES_STRING,
                                       description_pattern=_('«{field}» starts with {values} (case insensitive)'),
                                      ),
    ISTARTSWITH_NOT: ConditionOperator(_('Does not start with (case insensitive)'), '{}__istartswith', allowed_fieldtypes=FIELDTYPES_STRING, exclude=True,
                                       description_pattern=_('«{field}» does not start with {values} (case insensitive)'),
                                      ),
    ENDSWITH:        ConditionOperator(_('Ends with'),                              '{}__endswith',    allowed_fieldtypes=FIELDTYPES_STRING,
                                       description_pattern=_('«{field}» ends with {values}'),
                                      ),
    ENDSWITH_NOT:    ConditionOperator(_('Does not end with'),                      '{}__endswith',    allowed_fieldtypes=FIELDTYPES_STRING, exclude=True,
                                       description_pattern=_('«{field}» does not end with {values}'),
                                      ),
    IENDSWITH:       ConditionOperator(_('Ends with (case insensitive)'),           '{}__iendswith',   allowed_fieldtypes=FIELDTYPES_STRING,
                                       description_pattern=_('«{field}» ends with {values} (case insensitive)'),
                                      ),
    IENDSWITH_NOT:   ConditionOperator(_('Does not end with (case insensitive)'),   '{}__iendswith',   allowed_fieldtypes=FIELDTYPES_STRING, exclude=True,
                                       description_pattern=_('«{field}» does not end with {values} (case insensitive)'),
                                      ),

    # ISEMPTY: IsEmptyOperator(_('Is empty'), allowed_fieldtypes=FIELDTYPES_NULLABLE),
    ISEMPTY: IsEmptyOperator(_('Is empty')),
    RANGE:   RangeOperator(_('Range')),
}
