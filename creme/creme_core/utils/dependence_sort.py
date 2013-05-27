# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013  Hybird
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

from future_builtins import map


class DependenciesLoopError(Exception):
    pass

#TODO: can we recycle the temporary lists or do an 'in-place' implementation ?
def dependence_sort(l, get_key, get_dependencies):
    """Sort a sequence of objects that have dependencies between them
    eg: if A depends on B, B will be before A.
    @param l Sequence
    @param get_key Callable that take one element from 'l', and returns a 
           unique key (in 'l') that identifies this element.
    @param get_dependencies Callable that take one element from 'l', and 
           returns a list(-like) of keys (see get_key()).
    @return A sorted list wich contains all elements from l.
    @throws DependenciesLoopError
    """
    sortedl = [] #sorted elements
    resolved = set() #dependencies that have been resolved (ie: sorted)

    while True:
        nosortedl = [] #elements that are not sorted yet
        changed = False

        for e in l:
            if all(dep in resolved for dep in get_dependencies(e)):
                sortedl.append(e)
                resolved.add(get_key(e))
                changed = True
            else:
                nosortedl.append(e)

        if not changed:
            if nosortedl:
                raise DependenciesLoopError('Loop dependencies between:\n'
                                            ' - %s\n'
                                            'No problem with:\n'
                                            ' - %s\n' % ('\n - '.join(map(str, nosortedl)),
                                                         '\n - '.join(map(str, sortedl)),
                                                        )
                                           )

            break

        l = nosortedl

    return sortedl
