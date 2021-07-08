# -*- coding: utf-8 -*-

################################################################################
#
# Copyright (c) 2016-2021 Hybird
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
from typing import (
    Any,
    DefaultDict,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
)

from django.db import DEFAULT_DB_ALIAS, connections
from django.db.models import ForeignKey, Model

from ..models import CaseSensitivity
from .meta import FieldInfo


def get_indexes_columns(model: Type[Model]) -> Iterator[List[str]]:
    """Generator which yields the columns corresponding to a model-s indexes.
    @param model: A class inheriting DjangoModel.
    @yield Lists of strings (field/columns names).
    """
    connection = connections[DEFAULT_DB_ALIAS]

    for constr_info in connection.introspection.get_constraints(
        connection.cursor(), model._meta.db_table,
    ).values():
        if constr_info['index']:
            yield constr_info['columns']


def build_columns_key(columns: Iterable[str]) -> str:
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
    return ''.join(f'#{column}#' for column in columns)


# NB: 'maxsize=None' => avoid locking (number of models is small)
@lru_cache(maxsize=None)
def get_keyed_indexes_columns(model: Type[Model]) -> Tuple[Tuple[str, Tuple[str, ...]], ...]:
    """Build a cached structure which contains information about indexes of a model
    @param model: A class inheriting DjangoModel.
    @return A tuple of tuples (string_key, field_names_tuple).
    @see build_columns_key() for the key.

    NB: the return value is immutable, so the cached values can not be altered.
    """
    return tuple(
        (build_columns_key(columns), tuple(columns))
        for columns in get_indexes_columns(model)
    )


def get_indexed_ordering(model: Type[Model],
                         fields_pattern: Iterable[str],
                         ) -> Optional[Tuple[str, ...]]:
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
                raise ValueError(f'Successive wildcards are forbidden: {fields_pattern}')

            previous_was_wildcard = True
        else:
            previous_was_wildcard = False

            if field_name.startswith('-'):
                reversed_count += 1
                field_name = field_name[1:]

        asc_fnames.append(field_name)

    if reversed_count and reversed_count != len(asc_fnames) - wildcard_count:
        # Columns of the indexes are only ASC, so all field names must have the same order.
        return None

    indexes = get_keyed_indexes_columns(model)

    if asc_fnames[-1] == '*':
        asc_fnames.pop()

    pattern = ''.join(f'#{name}#*' if name != '*' else name for name in asc_fnames)

    for index_key, ordering in indexes:
        if fnmatch(index_key, pattern):
            if reversed_count:
                ordering = tuple(f'-{i}' for i in ordering)

            return ordering

    return None


# TODO: ManyToManyField too ?
def populate_related(instances: Sequence[Model],
                     field_names: Iterable[str],
                     ) -> None:
    """Retrieve the given ForeignKeys values for some instances, in order to
    reduce the number of DB queries.

    @param instances: Sequence of instances with the _same_ ContentType.
                      NB: iterated several times -> not an iterator.
    @param field_names: Sequence of strings representing field names ala django
           (eg: 'user__username').
    """
    if not instances:
        return

    # Model/ID/Instances => big_instances_cache[my_model].get(my_id)
    global_cache: DefaultDict[Type[Model], Dict[Any, Model]] = defaultdict(dict)

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
            attr_name = field.get_attname()

            rel_model = field.remote_field.model
            cached = global_cache[rel_model]
            new_ids = new_ids_per_model[rel_model]

            for instance in instances:
                if not field.is_cached(instance):
                    attr_id = getattr(instance, attr_name)

                    if attr_id and attr_id not in cached:
                        new_ids.add(attr_id)

        # Step 2: we retrieve all the new instances (ie: not already cached) needed by this level
        #         with our grouped queries, & fill the cache.
        for rel_model, ids in new_ids_per_model.items():
            global_cache[rel_model].update(
                (o.pk, o)
                for o in rel_model._default_manager.filter(pk__in=ids)
            )

        # Step 3: we store the retrieved instances (level N+1) in our given instances (level N+1).
        #         & we build the works for the level N+1 for these new instances.
        for instances, field_info, field in _iter_works(works):
            fname = field.name
            attr_name  = field.get_attname()
            # cache_name = field.get_cache_name()

            get_cached = global_cache[field.remote_field.model].get
            related_instances = []

            for instance in instances:
                attr_id = getattr(instance, attr_name)

                if attr_id:
                    try:
                        rel_instance = field.get_cached_value(instance)
                    except KeyError:
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


# NB: 'maxsize=None' => avoid locking (number of models is small)
@lru_cache(maxsize=None)
def is_db_equal_case_sensitive() -> bool:  # TODO: argument "db" for multi-db env ?
    """Is the main database case sensitive or not with the Django's operator
    "exact" ("=" in SQL).
    @return A boolean ; <True> means "case sensitive".

    NB: the return value is immutable, so the cached values can not be altered.
    """
    # NB: a line with <text == 'CasE'> must exist in DB ; see 'populate.py'.
    return not CaseSensitivity.objects.filter(text__exact='case').exists()


@lru_cache(maxsize=None)
def is_db_like_case_sensitive() -> bool:  # TODO: idem
    """Is the main database case sensitive or not with the Django's operators
    "contains/startswith/endswith" ("LIKE" in SQL).
    @return A boolean ; <True> means "case sensitive".

    NB: the return value is immutable, so the cached values can not be altered.
    """
    # NB: see is_db_equal_case_sensitive()
    return not CaseSensitivity.objects.filter(text__contains='case').exists()


# TODO: accept multiple/iterative order()/proceed() calls ?
class PreFetcher:
    """Regroup queries on same model (to retrieve instances by their PK)
    Accumulate calls to order(), & then build the pre-fetched cache with
    proceed().
    """
    def __init__(self):
        self._orders = defaultdict(set)
        self._prefetched: Optional[Dict[Type[Model], Dict[Any, Model]]] = None

    def get(self, model: Type[Model], pk) -> Optional[Model]:
        prefetched = self._prefetched
        if prefetched is None:
            raise RuntimeError('PreFetcher not filled (hint: call proceed())')

        return prefetched[model].get(pk)

    def order(self, model: Type[Model], pks: Iterable) -> 'PreFetcher':
        if self._prefetched is not None:
            raise RuntimeError('PreFetcher already (hint: call order() before proceed() only)')

        self._orders[model].update(pks)

        return self

    def proceed(self) -> 'PreFetcher':
        if self._prefetched is not None:
            raise RuntimeError('PreFetcher already (hint: call proceed() only once)')

        self._prefetched = {
            model: model._default_manager.in_bulk(pks)
            for model, pks in self._orders.items()
        }

        return self
