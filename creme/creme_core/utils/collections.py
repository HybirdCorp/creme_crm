# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from __future__ import absolute_import #for standard 'collections' module

import collections
from sys import maxint


class LimitedList(object):
    def __init__(self, max_size):
        self._max_size = max_size
        self._size = 0
        self._data = []

    def append(self, obj):
        if self._size < self._max_size:
            self._data.append(obj)
        self._size += 1

    @property
    def max_size(self):
        return self._max_size

    def __len__(self):
        return self._size

    def __nonzero__(self):
        return bool(self._size)

    def __iter__(self):
        return iter(self._data)

    def __repr__(self):
        return repr(self._data)


class ClassKeyedMap(object):
    """A kind of dictionnary where key must be classes (with single inheritance).
    When a value is not found, the value of the nearest parent (in the class
    inheritage meaning), in the map, is used. If there is no parent class,
    a default value given a construction is used.
    No get() method because there is no 'default' argument.
    """
    def __init__(self, items=(), default=None):
        self._data = dict(items)
        self._default = default

    @staticmethod
    def _nearest_parent_class(klass, classes): #TODO: in utils ??
        #class Klass1(object): pass
        #class Klass2(Klass1): pass
        #Klass2.mro() #=> [<class 'Klass2'>, <class 'Klass1'>, <type 'object'>]
        # -> So the smallest order corresponds to the nearest class
        get_order = {cls: i for i, cls in enumerate(klass.mro())}.get

        return sorted(classes, key=lambda cls: get_order(cls, maxint))[0]

    def __getitem__(self, key_class):
        """There is no default argument, beacuse it is given at construction ;
        the default value is used to fill the cache (so there are side effects),
        and a different default value could lead to strange behaviours.
        """
        data = self._data

        try:
            key_class_value = data[key_class]
        except KeyError:
            #TODO: improve algo with complex registration parent/child with holes + annoying order 
            #      VS we want to control the behaviour with instaleld apps order ??
            family = [cls for cls in data.iterkeys() if issubclass(key_class, cls)]

            if family:
                key_class_value = data[self._nearest_parent_class(key_class, family)]
            else:
                key_class_value = self._default

            #NB: we insert the missing value to keep an amortized O(1) complexity on future calls.
            data[key_class] = key_class_value

        return key_class_value

    def __setitem__(self, key_class, value):
        data = self._data

        for cls in data.iterkeys():
            if issubclass(cls, key_class):
                data[cls] = value

        data[key_class] = value

        #return value #NB: useless, python does it for us

    def __contains__(self, key):
        return key in self._data

    #def __eq__(self, other): #would be an heavy operation....

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __nonzero__(self):
        return bool(self._data)

    def __repr__(self):
        return 'ClassKeyedMap(%s, default=%s)' % (repr(list(self.items())),
                                                  repr(self.default),
                                                 )

    @property
    def default(self):
        return self._default

    def items(self): #NB: already Py3K ready :)
        return self._data.iteritems()

    def keys(self): #NB: already Py3K ready :)
        return self._data.iterkeys()

    def values(self): #NB: already Py3K ready :)
        return self._data.itervalues()


################################################################################
#    Copyright (C) 2009-2012 Raymond Hettinger
#
#    Permission is hereby granted, free of charge, to any person obtaining a 
#    copy of this software and associated documentation files (the "Software"),
#    to deal in the Software without restriction, including without limitation
#    the rights touse, copy, modify, merge, publish, distribute, sublicense,
#    and/or sell copies of the Software, and to permit persons to whom the
#    Software is furnished to do so, subject to the following conditions:

#    The above copyright notice and this permission notice shall be included
#    in all copies or substantial portions of the Software.

#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS 
#    OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL 
#    THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#    DEALINGS IN THE SOFTWARE.
################################################################################

# Found at http://code.activestate.com/recipes/576694/

class OrderedSet(collections.MutableSet):
    """Set that remembers original insertion order.
    Implementation based on a doubly linked link and an internal dictionary.
    This design gives OrderedSet the same big-Oh running times as regular sets
    including O(1) adds, removes, and lookups as well as O(n) iteration.
    """
    def __init__(self, iterable=None):
        self.end = end = []
        end += [None, end, end]  # sentinel node for doubly linked list
        self.map = {}            # key --> [key, prev, next]
        if iterable is not None:
            self |= iterable

    def __len__(self):
        return len(self.map)

    def __contains__(self, key):
        return key in self.map

    def add(self, key):
        if key not in self.map:
            end = self.end
            curr = end[1]
            curr[2] = end[1] = self.map[key] = [key, curr, end]

    def discard(self, key):
        if key in self.map:
            key, prev, next = self.map.pop(key)
            prev[2] = next
            next[1] = prev

    def __iter__(self):
        end = self.end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def pop(self, last=True):
        if not self:
            raise KeyError('set is empty')
        key = self.end[1][0] if last else self.end[2][0]
        self.discard(key)
        return key

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, list(self))

    def __eq__(self, other):
        if isinstance(other, OrderedSet):
            return len(self) == len(other) and list(self) == list(other)
        return set(self) == set(other)
