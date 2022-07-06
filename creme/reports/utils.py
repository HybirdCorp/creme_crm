################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2020  Hybird
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
from itertools import zip_longest

from .constants import DATETIME_FILTER_FORMAT


def encode_datetime(date):
    return date.strftime(DATETIME_FILTER_FORMAT) if date else None


def decode_datetime(date_str):
    return datetime.strptime(date_str, DATETIME_FILTER_FORMAT) if date_str else None


def expand_sparse_iterator(sparse_iterator, default_value):
    """
    Expands a 'sparse' collection with a default value where the collection
    misses existing indices.
    An example 'full' collection [1,0,0,0,3,5] could be compressed as a 'sparse'
    collection like :
       [{'index': 0, 'value': 1}, {'index': 4, 'value': 3}, {'index': 5, 'value': 5}]
       represented as
       [(0, 1), (4, 3), (5, 5)].
    This method takes an iterator on such a sparse collection and yields a
    default value for the missing indices, resulting in the original full collection.
    """
    try:
        current_index, current_value = next(sparse_iterator)
    except StopIteration:  # It's deprecated to raise a StopIteration in a generator
        pass
    else:
        yield current_value

        for next_index, next_value in sparse_iterator:
            for _times in range(abs(current_index - next_index) - 1):
                yield default_value
            yield next_value
            current_index = next_index


# TODO: this could be interesting in creme_core.utils
def sparsezip(full_collection, sparse_collection, default_value):
    """Zips a 'full' collection with a 'sparse' collection by expanding the
    latter using expand_sparse_iterator()
    """
    yield from zip_longest(full_collection,
                           expand_sparse_iterator(iter(sparse_collection), default_value),
                           fillvalue=default_value)
