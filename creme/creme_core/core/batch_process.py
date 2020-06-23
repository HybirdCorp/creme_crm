# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

from collections import OrderedDict
from itertools import chain
from typing import Any, Callable, Optional, Type

from django.db import models
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.models import CremeEntity


class CastError(Exception):
    pass


def cast_2_str(value) -> str:
    return str(value)


def cast_2_positive_int(value) -> int:
    try:
        value = int(value)
    except (ValueError, TypeError) as e:
        raise CastError(gettext('enter a whole number')) from e

    if value < 1:
        raise CastError(gettext('enter a positive number'))

    return value


class BatchOperator:
    __slots__ = ('id', '_name', '_function', '_cast_function', '_need_arg')

    def __init__(self,
                 id_: str,
                 name: str,
                 function: Callable,
                 cast_function: Callable[[Any], Any] = cast_2_str):
        self.id = id_
        self._name = name
        self._function = function
        self._cast_function = cast_function
        self._need_arg: bool = (function.__code__.co_argcount > 1)

    def __str__(self):
        return str(self._name)

    def __call__(self, x, *args):
        if self._need_arg:
            return self._function(x, *args)

        return self._function(x)

    def cast(self, value):
        return self._cast_function(value)  # Can raise CastError

    @property
    def need_arg(self) -> bool:
        return self._need_arg


class BatchOperatorManager:
    _CAT_STR = 'str'
    _CAT_INT = 'int'

    _OPERATOR_MAP = {
        # TODO: loop & factorise
        _CAT_STR: OrderedDict([
            ('upper',  BatchOperator('upper',  _('To upper case'), lambda x: x.upper())),
            ('lower',  BatchOperator('lower',  _('To lower case'), lambda x: x.lower())),
            ('title',  BatchOperator('title',  _('Initial to upper case'), lambda x: x.title())),
            ('prefix', BatchOperator('prefix', _('Prefix'), (lambda x, prefix: prefix + x))),
            ('suffix', BatchOperator('suffix', _('Suffix'), (lambda x, suffix: x + suffix))),
            (
                'rm_substr',
                BatchOperator(
                    'rm_substr', _('Remove a sub-string'),
                    (lambda x, substr: x.replace(substr, '')),
                ),
            ),
            (
                'rm_start',
                BatchOperator(
                    'rm_start', _('Remove the start (N characters)'),
                    (lambda x, size: x[size:]),
                    cast_function=cast_2_positive_int,
                ),
            ),
            (
                'rm_end',
                BatchOperator(
                    'rm_end', _('Remove the end (N characters)'),
                    (lambda x, size: x[:-size]),
                    cast_function=cast_2_positive_int,
                )
            ),
        ]),
        _CAT_INT: OrderedDict([
            (
                'add_int',
                BatchOperator(
                    'add_int', _('Add'), (lambda x, y: x + y),
                    cast_function=cast_2_positive_int,
                ),
            ),
            (
                'sub_int',
                BatchOperator(
                    'sub_int', _('Subtract'), (lambda x, y: x - y),
                    cast_function=cast_2_positive_int,
                ),
            ),
            (
                'mul_int',
                BatchOperator(
                    'mul_int', _('Multiply'), (lambda x, y: x * y),
                    cast_function=cast_2_positive_int,
                ),
            ),
            (
                'div_int',
                BatchOperator(
                    'div_int', _('Divide'),   (lambda x, y: x // y),
                    cast_function=cast_2_positive_int
                ),
            ),
        ]),
    }

    _OPERATOR_FIELD_MATRIX = {
        models.CharField:       _CAT_STR,
        models.TextField:       _CAT_STR,
        models.IntegerField:    _CAT_INT,
    }

    def _get_category(self, model_field_type) -> Optional[str]:
        for field_cls, cat in self._OPERATOR_FIELD_MATRIX.items():
            if issubclass(model_field_type, field_cls):
                return cat

        return None

    def get(self, model_field_type, operator_name: str) -> Optional[BatchOperator]:
        """Get the wanted BatchOperator object.
        @param model_field_type: Class inheriting <django.db.model.Field>.
        """
        category = self._get_category(model_field_type)
        if category:
            return self._OPERATOR_MAP[category].get(operator_name)

        return None

    @property
    def managed_fields(self):
        """@return Iterator on all classes of modelfield that have BatchOperator."""
        return self._OPERATOR_FIELD_MATRIX.keys()

    def operators(self, model_field_type=None):
        """Iterator that yields (operator_name, operator_instance) tuples
        @param model_field_type: Class inheriting django.db.model.Field.
                                 <None> means "all operators".
        """
        if model_field_type:
            category = self._get_category(model_field_type)
            ops = self._OPERATOR_MAP[category] if category else {}

            return ops.items()

        return chain.from_iterable(ops.items() for ops in self._OPERATOR_MAP.values())


batch_operator_manager = BatchOperatorManager()


class BatchAction:
    __slots__ = ('_model', '_field_name', '_operator', '_value')

    class InvalidOperator(Exception):
        pass

    class ValueError(Exception):
        pass

    def __init__(self, model: Type[CremeEntity], field_name: str, operator_name: str, value):
        self._field_name = field_name
        self._model = model
        field = model._meta.get_field(field_name)
        operator = batch_operator_manager.get(field.__class__, operator_name)

        if not operator:
            raise BatchAction.InvalidOperator()

        if operator.need_arg and not value:
            raise BatchAction.ValueError(
                gettext("The operator '{}' needs a value.").format(operator)
            )

        self._operator: BatchOperator = operator

        try:
            self._value = operator.cast(value)
        except CastError as e:
            raise BatchAction.ValueError(
                gettext('{operator} : {message}.').format(
                    operator=operator,
                    message=e,
                )
            ) from e

    def __call__(self, entity: CremeEntity) -> bool:
        """The action's operator is computed with the given entity
        (on the field indicated by action-field and using the action-value),
        and the entity field's value is updated.
        Something like: entity.foo = function(entity.foo)
        @return True if the entity has changed.
        """
        fname = self._field_name
        old_value = getattr(entity, fname)

        if old_value is not None:
            new_value = self._operator(old_value, self._value)

            if old_value != new_value:
                setattr(entity, fname, new_value)
                return True

        return False

    def __str__(self):
        op = self._operator
        field = self._model._meta.get_field(self._field_name).verbose_name

        return (
            gettext('{field} ➔ {operator}').format(field=field, operator=op)
            if not op.need_arg else
            gettext('{field} ➔ {operator}: «{value}»').format(
                field=field, operator=op, value=self._value,
            )
        )
