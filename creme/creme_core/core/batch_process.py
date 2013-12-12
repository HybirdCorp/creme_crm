# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from itertools import chain

from django.db import models
from django.utils.translation import ugettext_lazy as _, ugettext


class CastError(Exception):
    pass


def cast_2_str(value):
    return str(value)

#def cast_2_int(value):
    #try:
        #value = int(value)
    #except (ValueError, TypeError):
        #raise CastError(ugettext('enter a whole number'))

    #return value

def cast_2_positive_int(value):
    try:
        value = int(value)
    except (ValueError, TypeError):
        raise CastError(ugettext('enter a whole number'))

    if value < 1:
        raise CastError(ugettext('enter a positive number'))

    return value


class BatchOperator(object):
    __slots__ = ('_name', '_function', '_cast_function', '_need_arg')

    def __init__(self, name, function, cast_function=cast_2_str):
        self._name = name
        self._function = function
        self._cast_function = cast_function
        self._need_arg = (function.func_code.co_argcount > 1)

    def __unicode__(self):
        return unicode(self._name)

    def __call__(self, x, *args):
        if self._need_arg:
            return self._function(x, *args)

        return self._function(x)

    def cast(self, value):
        return self._cast_function(value) #can raise CastError

    @property
    def need_arg(self):
        return self._need_arg


class BatchOperatorManager(object):
    _CAT_STR = 'str'
    _CAT_INT = 'int'

    _OPERATOR_MAP = {
            _CAT_STR: {'upper':     BatchOperator(_('To upper case'),                   lambda x: x.upper()),
                       'lower':     BatchOperator(_('To lower case'),                   lambda x: x.lower()),
                       'title':     BatchOperator(_('Initial to upper case'),           lambda x: x.title()),
                       'prefix':    BatchOperator(_('Prefix'),                          (lambda x, prefix: prefix + x)),
                       'suffix':    BatchOperator(_('Suffix'),                          (lambda x, suffix: x + suffix)),
                       'rm_substr': BatchOperator(_('Remove a sub-string'),             (lambda x, substr: x.replace(substr, ''))),
                       'rm_start':  BatchOperator(_('Remove the start (N characters)'), (lambda x, size: x[size:]),  cast_function=cast_2_positive_int),
                       'rm_end':    BatchOperator(_('Remove the end (N characters)'),   (lambda x, size: x[:-size]), cast_function=cast_2_positive_int),
                      },
            _CAT_INT: {'add_int':   BatchOperator(_('Add'),      (lambda x, y: x + y),  cast_function=cast_2_positive_int),
                       'sub_int':   BatchOperator(_('Subtract'), (lambda x, y: x - y),  cast_function=cast_2_positive_int),
                       'mul_int':   BatchOperator(_('Multiply'), (lambda x, y: x * y),  cast_function=cast_2_positive_int),
                       'div_int':   BatchOperator(_('Divide'),   (lambda x, y: x // y), cast_function=cast_2_positive_int),
                      },
        }

    _OPERATOR_FIELD_MATRIX = {
            models.CharField:       _CAT_STR,
            models.TextField:       _CAT_STR,
            models.IntegerField:    _CAT_INT,
        }

    def _get_category(self, model_field_type):
        #return self._OPERATOR_FIELD_MATRIX.get(model_field_type)
        for field_cls, cat in self._OPERATOR_FIELD_MATRIX.iteritems():
            if issubclass(model_field_type, field_cls):
                return cat

    def get(self, model_field_type, operator_name):
        """Get the wanted BatchOperator object.
        @param model_field_type Class inheriting django.db.model.Field.
        """
        category = self._get_category(model_field_type)
        if category:
            return self._OPERATOR_MAP[category].get(operator_name)

    @property
    def managed_fields(self):
        """@return Iterator on all classes of modelfield that have BatchOperator."""
        return self._OPERATOR_FIELD_MATRIX.iterkeys()

    def operators(self, model_field_type=None):
        """Iterator that yields (operator_name, operator_instance) tuples
        @param model_field_type Class inheriting django.db.model.Field.
                                None means "all operators".
        """
        if model_field_type:
            category = self._get_category(model_field_type)
            ops = self._OPERATOR_MAP[category] if category else {}

            return ops.iteritems()

        return chain.from_iterable(ops.iteritems() for ops in self._OPERATOR_MAP.itervalues())


batch_operator_manager = BatchOperatorManager()


class BatchAction(object):
    __slots__ = ('_field_name', '_operator', '_value')

    class InvalidOperator(Exception):
        pass

    class ValueError(Exception):
        pass

    def __init__(self, model, field_name, operator_name, value):
        self._field_name = field_name
        field = model._meta.get_field(field_name)
        self._operator = operator = batch_operator_manager.get(field.__class__, operator_name)

        if not operator:
            raise BatchAction.InvalidOperator()

        if operator.need_arg and not value:
            raise BatchAction.ValueError(ugettext(u"The operator '%s' need a value.") % operator)

        try:
            self._value = operator.cast(value)
        except CastError as e:
            raise BatchAction.ValueError(ugettext(u'%(operator)s : %(message)s.') % {
                                                'operator': operator,
                                                'message':  e,
                                            }
                                        )

    def __call__(self, entity):
        """entity.foo = function(entity.foo)
        @return True The entity has changed.
        """
        fname = self._field_name
        old_value = getattr(entity, fname)

        if old_value is not None:
            new_value = self._operator(old_value, self._value)

            if old_value != new_value:
                setattr(entity, fname, new_value)
                return True

        return False
