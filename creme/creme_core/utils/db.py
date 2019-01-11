# -*- coding: utf-8 -*-

################################################################################
#
# Copyright (c) 2016-2018 Hybird
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

from collections import defaultdict
from fnmatch import fnmatch
from functools import lru_cache
import warnings

from django.db import connections, DEFAULT_DB_ALIAS
from django.db.models import ForeignKey
from django.db.transaction import atomic

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
                                 .values():
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
    return ''.join('#{}#'.format(column) for column in columns)


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
                raise ValueError('Successive wildcards are forbidden: {}'.format(fields_pattern))

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

    pattern = ''.join('#{}#*'.format(name) if name != '*' else name
                        for name in asc_fnames
                     )

    for index_key, ordering in indexes:
        if fnmatch(index_key, pattern):
            if reversed_count:
                ordering = tuple('-{}'.format(i) for i in ordering)

            return ordering

    return None


# TODO: ManyToManyField too ?
def populate_related(instances, field_names):
    """Retrieve the given ForeignKeys values for some instances, in order to
    reduce the number of DB queries.

    @param instances: Sequence of instances with the _same_ ContentType.
                      NB: iterated several times -> not an iterator.
    @param field_names: Sequence of strings representing field names ala django (eg: 'user__username').
    """
    if not instances:
        return

    # Model/ID/Instances => big_instances_cache[my_model].get(my_id)
    global_cache = defaultdict(dict)

    def _iter_works(works):
        for instances, fields_info in works:
            for field_info in fields_info:
                if not field_info:
                    continue

                field = field_info[0]

                if not isinstance(field, ForeignKey):
                    continue

                yield instances, field_info, field

    def _populate_depth(works):
        new_ids_per_model = defaultdict(set)  # Key=model ; values=IDs
        next_works = []

        # Step 1: we group all FK related to the same model, in order to group queries.
        for instances, field_info, field in _iter_works(works):
            attr_name  = field.get_attname()
            cache_name = field.get_cache_name()

            # rel_model = field.rel.to
            rel_model = field.remote_field.model
            cached = global_cache[rel_model]
            new_ids = new_ids_per_model[rel_model]

            for instance in instances:
                if not hasattr(instance, cache_name):
                    attr_id = getattr(instance, attr_name)

                    if attr_id and attr_id not in cached:
                        new_ids.add(attr_id)

        # Step 2: we retrieve all the new instances (ie: not already cached) needed by this level
        #         with our grouped queries, & fill the cache.
        for rel_model, ids in new_ids_per_model.items():
            global_cache[rel_model] \
                        .update((o.pk, o)
                                   for o in rel_model._default_manager.filter(pk__in=ids)
                               )

        # Step 3: we store the retrieved instances (level N+1) in our given instances (level N+1).
        #         & we build the works for the level N+1 for these new instances.
        for instances, field_info, field in _iter_works(works):
            fname = field.name
            attr_name  = field.get_attname()
            cache_name = field.get_cache_name()

            # get_cached = global_cache[field.rel.to].get
            get_cached = global_cache[field.remote_field.model].get
            related_instances = []

            for instance in instances:
                attr_id = getattr(instance, attr_name)

                if attr_id:
                    if hasattr(instance, cache_name):
                        rel_instance = getattr(instance, fname)
                    else:
                        rel_instance = get_cached(attr_id)
                        setattr(instance, fname, rel_instance)

                    related_instances.append(rel_instance)

            if related_instances:
                next_works.append((related_instances, [field_info[1:]]))

        return next_works

    base_model = instances[0].__class__

    # NB: in a 'work':
    #  [0] - The instances must have the same model.
    #  [1] - The FieldInfo objects must be related to this model.
    works = [(instances, [FieldInfo(base_model, deep_fname) for deep_fname in field_names])]

    while works:
        works = _populate_depth(works)


@atomic
def reorder_instances(moved_instance, new_order, queryset=None, order_field='order'):
    """ Change the order of an instance inside a set of ordered instances (ie:
    a QuerySet on a model with an integer field used for ordering).

    @param moved_instance: The instance which moves inside the sequence.
    @param new_order: The new order (integer) of 'moved_instance'. BEWARE, this order is a
                      1-based index in the sequence, and NOT the value of the ordering field.
                      (but after the call, it's teh same thing ; see below).
    @param queryset: The sequence to reorder. If not given, all the instances of the model are used.
    @param order_field: Name of the ordering field. Default is 'order'.

    @raises ValueError if 'moved_instance' is not found in the queryset.

    Notice: the values for 'order_field' are automatically re-mapped on [1, 2 ...]
            (so even if the global ordering of an instance has not changed, its field's value
             could have changed).
    """
    warnings.warn('creme_core.utils.db.reorder_instances() is deprecated ; '
                  'use creme_core.views.generic.order.ReorderInstances instead.',
                  DeprecationWarning
                 )

    if queryset is None:
        queryset = moved_instance.__class__._default_manager.all()

    instances = list(queryset.order_by(order_field).select_for_update())

    if new_order < 1 or new_order > len(instances):
        raise IndexError('Next order is out of range.')

    instances.pop(instances.index(moved_instance))
    instances.insert(new_order - 1, moved_instance)

    for index, instance in enumerate(instances, start=1):
        old_order = getattr(instance, order_field)

        if old_order != index:
            setattr(instance, order_field, index)
            instance.save(force_update=True, update_fields=(order_field,))
