# -*- coding: utf-8 -*-

################################################################################
#
# Copyright (c) 2013-2021 Hybird
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


class DependenciesLoopError(Exception):
    pass


# TODO: can we recycle the temporary lists or do an 'in-place' implementation ?
def dependence_sort(iterable, get_key, get_dependencies):
    """Sort a sequence of objects that have dependencies between them
    eg: if A depends on B, B will be before A.
    @param iterable: Sequence
    @param get_key: Callable that takes one element from 'l', and returns a
           unique key (in 'l') that identifies this element.
    @param get_dependencies: Callable that take one element from 'l', and
           returns a list(-like) of keys (see get_key()).
    @return A sorted list which contains all elements from l.
    @throws DependenciesLoopError.
    """
    ordered_list = []  # Sorted elements
    resolved = set()  # Dependencies that have been resolved (ie: sorted)

    while True:
        unordered_list = []  # Elements that are not sorted yet
        changed = False

        for e in iterable:
            # TODO: cache the dependencies ?
            if all(dep in resolved for dep in get_dependencies(e)):
                ordered_list.append(e)
                resolved.add(get_key(e))
                changed = True
            else:
                unordered_list.append(e)

        if not changed:
            if unordered_list:
                raise DependenciesLoopError(
                    'Loop dependencies between:\n'
                    ' - {}\n'
                    'No problem with:\n'
                    ' - {}\n'.format(
                        '\n - '.join(map(str, unordered_list)),
                        '\n - '.join(map(str, ordered_list)),
                    )
                )

            break

        iterable = unordered_list

    return ordered_list
