# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from logging import warning
from datetime import datetime

from creme_core.utils.imports import find_n_import

class DatetimeFilter(object):
    def __init__(self, name, verbose_name, func_beg, func_end):
        self.name = name
        self.verbose_name = verbose_name
        self.func_beg = func_beg
        self.func_end = func_end

    def get_begin(self):
        return self.func_beg(self, datetime.now())

    def get_end(self):
        return self.func_end(self, datetime.now())

    def __iter__(self):
        return iter((self.name, self.verbose_name))

class DatetimeFilterRegistry(object):
    def __init__(self):
        self._filters = {}

    def register(self, *to_register):
        filters = self._filters

        for name, filter in to_register:
            if filters.has_key(name):
                warning("Duplicate filter's id or filter registered twice : %s", name) #exception instead ???

            filters[name] = filter

    def get_filter(self, name):
        filters = self._filters
        if filters.has_key(name):
            return filters[name]

        return None

    def __iter__(self):
        return self._filters.iteritems()

    def itervalues(self):
        return self._filters.itervalues()

date_filters_registry = DatetimeFilterRegistry()

filters_imports = find_n_import("date_filters_register", ['to_register'])
for filter_import in filters_imports:
    date_filters_registry.register(*filter_import.to_register)