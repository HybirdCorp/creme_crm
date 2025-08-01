################################################################################
#
# Copyright (c) 2009-2025 Hybird
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
#
################################################################################

from collections.abc import (
    Callable,
    ItemsView,
    Iterable,
    Iterator,
    KeysView,
    MutableSet,
    ValuesView,
)
from sys import maxsize
from typing import Generic, TypeVar

T = TypeVar('T')


class LimitedList:
    def __init__(self, max_size: int):
        self._max_size = max_size
        self._size = 0
        self._data: list = []

    def append(self, obj):
        if self._size < self._max_size:
            self._data.append(obj)
        self._size += 1

    @property
    def max_size(self) -> int:
        return self._max_size

    def __len__(self):
        return self._size

    def __bool__(self):
        return bool(self._size)

    def __iter__(self):
        return iter(self._data)

    def __repr__(self):
        return repr(self._data)


class FluentList(list):
    "Enhanced list with fluent methods (i.e. can be chained) and a new method."
    def append(self, x):
        super().append(x)
        return self

    def clear(self):
        super().clear()
        return self

    def extend(self, xs):
        super().extend(xs)
        return self

    def insert(self, index, x):
        super().insert(index, x)
        return self

    def remove(self, x):
        super().remove(x)
        return self

    def reverse(self):
        super().reverse()
        return self

    def sort(self, **kwargs):
        super().sort(**kwargs)
        return self

    def replace(self, *, old, new):
        """Replace an element by another one (at the same place of course).

        @param old: Element to remove.
        @param new: Element to add.
        @return: self (fluent API).
        @raise ValueError: "old" is not found.
        """
        index = self.index(old)
        self.remove(old)
        self.insert(index, new)

        return self


class ClassKeyedMap(Generic[T]):
    """A kind of dictionary where key must be classes (with single inheritance).
    When a value is not found, the value of the nearest parent (in the class
    inheritance meaning), in the map, is used. If there is no parent class,
    a default value given a construction is used.
    No get() method because there is no 'default' argument.
    """
    def __init__(self,
                 items: Iterable[tuple[type, T]] = (),
                 default: T | None = None,
                 ):
        # self._data: dict[type, T | None] = OrderedDict(items)
        self._data: dict[type, T | None] = dict(items)
        self._default = default

    @staticmethod
    def _nearest_parent_class(klass, classes):  # TODO: in utils ??
        # class Klass1: pass
        # class Klass2(Klass1): pass
        # Klass2.mro() #=> [<class 'Klass2'>, <class 'Klass1'>, <type 'object'>]
        # -> So the smallest order corresponds to the nearest class
        get_order = {cls: i for i, cls in enumerate(klass.mro())}.get

        return sorted(classes, key=lambda cls: get_order(cls, maxsize))[0]

    def __getitem__(self, key_class: type) -> T | None:
        """There is no default argument, because it is given at construction ;
        the default value is used to fill the cache (so there are side effects),
        and a different default value could lead to strange behaviours.
        """
        data = self._data
        key_class_value: T | None

        try:
            key_class_value = data[key_class]
        except KeyError:
            # TODO: improve algo with complex registration parent/child with holes + annoying order
            #       VS we want to control the behaviour with installed apps order ??
            family = [cls for cls in data if issubclass(key_class, cls)]

            if family:
                key_class_value = data[self._nearest_parent_class(key_class, family)]
            else:
                key_class_value = self._default

            # NB: we insert the missing value to keep an amortized O(1) complexity on future calls.
            data[key_class] = key_class_value

        return key_class_value

    def __setitem__(self, key_class: type, value: T):
        data = self._data

        for cls in data:
            if issubclass(cls, key_class):
                data[cls] = value

        data[key_class] = value

        # return value  # NB: useless, python does it for us

    def __contains__(self, key: type):
        return key in self._data

    # def __eq__(self, other): # Would be an heavy operation....

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __bool__(self):
        return bool(self._data)

    def __repr__(self):
        return 'ClassKeyedMap({}, default={})'.format(
            repr([*self.items()]),
            repr(self.default),
        )

    @property
    def default(self) -> T | None:
        return self._default

    def items(self) -> ItemsView:
        return self._data.items()

    def keys(self) -> KeysView[type]:
        return self._data.keys()

    def values(self) -> ValuesView[T | None]:
        return self._data.values()


class InheritedDataChain(Generic[T]):
    """An associative collection where:
     - keys are classes
     - values are instances built by the collection itself
       (with a given factory -- like standard <collections.defaultdict>).

    The main feature is the 'chain()' method, which yields, for a given key-class,
    the values of this class _and_ of the parent class.
    So it's useful to retrieve accumulated data, like a method which would use
    the super()'s data too, but in a way external to some classes
    (it's more 'hookable'/extensible).
    """
    def __init__(self, default_factory: Callable[[], T]):
        """@param default_factory: A callable which returns an instance (typically a class)."""
        self._default_factory = default_factory
        self._data: dict[type, T] = {}

    def __contains__(self, key_class: type) -> bool:
        """@param key_class: A class."""
        return key_class in self._data

    def __delitem__(self, key_class: type) -> None:
        """
        @param key_class: A class.
        @raise: KeyError.
        """
        del self._data[key_class]

    def __getitem__(self, key_class: type) -> T:
        """
        @param key_class: A class.
        @return: An instance of 'default_factory' (see __init__) ;
                 the instance is created if it does not exist yet.
        """
        if not isinstance(key_class, type):
            raise ValueError('The key must be a class')

        try:
            return self._data[key_class]
        except KeyError:
            self._data[key_class] = value = self._default_factory()

            return value

    def chain(self, key_class: type, parent_first: bool = True) -> Iterator[T]:
        """A generator which yields the data related to the key-class (if they exist)
        and the data of the parent classes (if they exist), then data of the grand parent etc...

        @param key_class: A class ; data related to it & related to its parents
               classes are yielded.
        @param parent_first: If True (default value), the value related to a parent key-class
               is returned before the value related to its child key-class.
        @return: Instances of 'default_factory' (see __init__).
        """
        get_order = {cls: i for i, cls in enumerate(key_class.mro())}.get
        pondered_values = [
            (get_order(kls), value)
            for kls, value in self._data.items()
            if issubclass(key_class, kls)
        ]

        pondered_values.sort(key=lambda t: t[0], reverse=parent_first)

        # TODO: cache
        for __order, value in pondered_values:
            yield value

    def get(self, key_class: type, default=None):
        """Retrieve the value associated to a key-class if it exists.
        @param key_class: A class (the key).
        @param default: An object returned if the key is not found ; <None> by default.
        @return: An instance of 'default_factory', or 'default' if the key is not found.
        """
        return self._data.get(key_class, default)


################################################################################
#    Copyright (C) 2009-2018 Raymond Hettinger
#
#    Permission is hereby granted, free of charge, to any person obtaining a
#    copy of this software and associated documentation files (the "Software"),
#    to deal in the Software without restriction, including without limitation
#    the rights to use, copy, modify, merge, publish, distribute, sublicense,
#    and/or sell copies of the Software, and to permit persons to whom the
#    Software is furnished to do so, subject to the following conditions:
#
#    The above copyright notice and this permission notice shall be included
#    in all copies or substantial portions of the Software.
#
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
#    OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
#    THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#    DEALINGS IN THE SOFTWARE.
################################################################################

# Found at http://code.activestate.com/recipes/576694/

class OrderedSet(MutableSet):
    """Set that remembers original insertion order.
    Implementation based on a doubly linked list and an internal dictionary.
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
            return f'{self.__class__.__name__}()'

        return f'{self.__class__.__name__}({[*self]!r})'

    def __eq__(self, other):
        if isinstance(other, OrderedSet):
            return len(self) == len(other) and [*self] == [*other]

        return {*self} == {*other}
