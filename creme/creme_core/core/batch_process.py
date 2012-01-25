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

    def __init__(self, name, function, cast_function=cast_2_str, need_arg=False):
        self._name = name
        self._function = function
        self._cast_function = cast_function
        self._need_arg = need_arg

    def __unicode__(self):
        return unicode(self._name)

    def __call__(self, x, *args):
        #TODO: if self._need_arg ??
        return self._function(x, *args)

    def cast(self, value):
        return self._cast_function(value) #can raise CastError

    @property
    def need_arg(self):
        return self._need_arg


OPERATOR_MAP = {
        'upper':     BatchOperator(_('To upper case'),                   lambda x, *args: x.upper()),
        'lower':     BatchOperator(_('To lower case'),                   lambda x, *args: x.lower()),
        'title':     BatchOperator(_('Initial to upper case'),           lambda x, *args: x.title()),
        'prefix':    BatchOperator(_('Prefix'),                          (lambda x, prefix: prefix + x), need_arg=True),
        'suffix':    BatchOperator(_('Suffix'),                          (lambda x, suffix: x + suffix), need_arg=True),
        'rm_substr': BatchOperator(_('Remove a sub-string'),             (lambda x, substr: x.replace(substr, '')), need_arg=True),
        'rm_start':  BatchOperator(_('Remove the start (N characters)'), (lambda x, size: x[size:]), cast_function=cast_2_positive_int, need_arg=True),
        'rm_end':    BatchOperator(_('Remove the end (N characters)'),   (lambda x, size: x[:-size]), cast_function=cast_2_positive_int, need_arg=True),
    }


class BatchAction(object):
    __slots__ = ('_field_name', '_operator', '_value')

    class TypeError(Exception):
        pass

    def __init__(self, field_name, operator, value):
        self._field_name = field_name
        self._operator = operator

        try:
            self._value = operator.cast(value)
        except CastError as e:
            raise BatchAction.TypeError(ugettext(u'%(operator)s : %(message)s.') % {
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
        new_value = self._operator(old_value, self._value)

        if old_value != new_value:
            setattr(entity, fname, new_value)
            return True

        return False
