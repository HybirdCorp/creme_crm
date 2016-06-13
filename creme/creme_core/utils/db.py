# -*- coding: utf-8 -*-

################################################################################
#
# Copyright (c) 2016 Hybird
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
################################################################################

from __future__ import absolute_import  # for std 'collections'

from collections import defaultdict
from fnmatch import fnmatch

from django.db import connections, DEFAULT_DB_ALIAS
from django.db.models import ForeignKey
from django.utils.lru_cache import lru_cache

from .meta import FieldInfo


def get_indexes_columns(model):
    """Generator which yields the columns corresponding to a model-s indexes.
    @param model: A class inheriting DjangoModel.
    @return Lists of strings (field/columns names).
    """
    connection = connections[DEFAULT_DB_ALIAS]

    for constr_info in connection.introspection \
                                 .get_constraints(connection.cursor(),
                                                  model._meta.db_table,
                                                 ) \
                                 .itervalues():
        if constr_info['index']:
            yield constr_info['columns']


def build_columns_key(columns):
    """Build a key (string) for a sequence of field-names ;
     this key can be smartly filtered with a pattern.

    @param columns: Iterable of strings ; they represent field names.
    @return: A string key.
    @see get_indexed_ordering() for an example of pattern filtering.

    Example:
        build_keyed_columns(['sector_id'])
            => '#sector_id#'

        build_keyed_columns(('last_name', 'first_name'))
            => '#last_name##first_name#'
    """
    return ''.join('#%s#' % column for column in columns)


# NB: 'maxsize=None' => avoid locking (number of models is small)
@lru_cache(maxsize=None)
def get_keyed_indexes_columns(model):
    """Build a cached structure which contains information about indexes of a model
    @param model: A class inheriting DjangoModel.
    @return A tuple of tuples (string_key, field_names_tuple).
    @see build_columns_key() for the key.

    NB: the return value is immutable, so the cached values can not be altered.
    """
    return tuple((build_columns_key(columns), tuple(columns))
                    for columns in get_indexes_columns(model)
                )


def get_indexed_ordering(model, fields_pattern):
    """Search in the model's DB-indexes an ordering corresponding to a pattern,
    in order to have an efficient ordering.

    @param model: A class inheriting DjangoModel.
    @param fields_pattern: An iterable of strings ; these strings can be field names
           (related to 'model') or '*' (wildcard). The field names can start with '-'
           to indicates a DESC ordering. The wildcard can represent one or several fields.
           These fields names should correspond to real DB columns.
    @return A tuple of field names (which can start with '-'), or None if no corresponding
            index has been found.

    Example:
        [ If MyContact has an index ('last_name', 'first_name', 'email') ]
        get_indexed_ordering(MyContact, ['last_name', 'first_name'])
        get_indexed_ordering(MyContact, ['last_name', '*', 'email'])
        get_indexed_ordering(MyContact, ['last_name', '*'])
        get_indexed_ordering(MyContact, ['last_name'])
            => these calls will return ('last_name', 'first_name', 'email')

        get_indexed_ordering(MyContact, ['-last_name', '-first_name'])
            => ('-last_name', '-first_name', '-email')

    The (exploded) tuple can be given to the method QuerySet.order_by():
        ordering = get_indexed_ordering(MyContact, ...)

        if ordering is not None:
            MyContact.objects.filter(...).order_by(*ordering)

    NB #1: the validity of field names in not checked ; if you give an invalid
           field name, it simply won't be find in the indexes.
    NB #2: The Django introspection code returns the indexes without ASC/DESC
           information (& MySQL builds ASC indexes -- on 5.6 version at least)
           so you should not create indexes which mix ASC & DESC columns.
    """
    asc_fnames = []
    reversed_count = 0
    wildcard_count = 0
    previous_was_wildcard = False

    for field_name in fields_pattern:
        if field_name == '*':
            wildcard_count += 1

            if previous_was_wildcard:
                raise ValueError('Successive wildcards are forbidden: %s' % fields_pattern)

            previous_was_wildcard = True
        else:
            previous_was_wildcard = False

            if field_name.startswith('-'):
                reversed_count += 1
                field_name = field_name[1:]

        asc_fnames.append(field_name)

    if reversed_count and reversed_count != len(asc_fnames) - wildcard_count :
        # Columns of the indexes are only ASC, so all field names must have the same order.
        return None

    indexes = get_keyed_indexes_columns(model)

    if asc_fnames[-1] == '*':
        asc_fnames.pop()

    pattern = ''.join('#%s#*' % name if name != '*' else name
                        for name in asc_fnames
                     )

    for index_key, ordering in indexes:
        if fnmatch(index_key, pattern):
            if reversed_count:
                ordering = tuple('-%s' % i for i in ordering)

            return ordering

    return None


# TODO: ManyToManyField too ?
def populate_related(instances, field_names):
    """Retrieve the given ForeignKeys values for some instances, in order to
    reduce the number of DB queries.

    @param instances: Sequence of instances with the _same_ ContentType.
                      NB: iterated several times -> not an iterator.
    @param field_names: Sequence of strings representing field names.
    """
    if not instances:
        return

    def _populate_depth(fields_info, instances):
        fields_per_model = defaultdict(list)
        next_fields_info = []  # FieldInfo instances for the deeper fields
        next_instances = ()  # Related instances of this level => instances of the deeper level

        for field_info in fields_info:
            if field_info:
                field = field_info[0]

                if isinstance(field, ForeignKey):
                    fields_per_model[field.rel.to].append(field)
                    next_fields_info.append(field_info[1:])

        for model, fields in fields_per_model.iteritems():
            ids = set()
            fill_info = []

            for field in fields:
                fname = field.name
                att_name = field.get_attname()
                cache_name = field.get_cache_name()

                for instance in instances:
                    if not hasattr(instance, cache_name):
                        attr_id = getattr(instance, att_name)
                        if attr_id:
                            ids.add(attr_id)
                            fill_info.append((instance, fname, att_name, attr_id))

            if ids:
                next_instances = model._default_manager.filter(pk__in=ids)
                attr_values = {o.pk: o for o in next_instances}

                for instance, fname, att_name, attr_id in fill_info:
                    setattr(instance, fname, attr_values[getattr(instance, att_name)])

        return next_fields_info, next_instances

    base_model = instances[0].__class__
    fields_info = [FieldInfo(base_model, fname) for fname in field_names]

    while fields_info:
        fields_info, instances = _populate_depth(fields_info, instances)
