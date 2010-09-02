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

from imp import find_module
from logging import warning
from datetime import datetime

from django.conf import settings

def find_n_import(filename, imports):
    results = []
    for app in settings.INSTALLED_APPS:
        try:
            find_module(filename, __import__(app, {}, {}, [app.split(".")[-1]]).__path__)
        except ImportError, e:
            # there is no app report_backend_register.py, skip it
            continue

        results.append(__import__("%s.%s" % (app, filename) , globals(), locals(), imports, -1))
    return results


class ReportBackendRegistry(object):
    def __init__(self):
        self._backends = {}

    def register(self, *to_register):
        backends = self._backends

        for name, backend in to_register:
            if backends.has_key(name):
                warning("Duplicate backend's id or backend registered twice : %s", name) #exception instead ???

            backends[name] = backend

    def get_backend(self, name):
        backends = self._backends
        if backends.has_key(name):
            return backends[name]

        return None

    def __iter__(self):
        return self._backends.iteritems()

    def itervalues(self):
        return self._backends.itervalues()


report_backend_registry = ReportBackendRegistry()

backends_imports = find_n_import("report_backend_register", ['to_register'])
for backend_import in backends_imports:
    report_backend_registry.register(*backend_import.to_register)

class ReportDatetimeFilter(object):
    def __init__(self, name, verbose_name, func_beg, func_end):
        self.name = name
        self.verbose_name = verbose_name
        self.func_beg = func_beg
        self.func_end = func_end

    def get_begin(self):
        return self.func_beg(self, datetime.now())

    def get_end(self):
        return self.func_end(self, datetime.now())

class ReportDatetimeFilterRegistry(object):
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

report_filters_registry = ReportDatetimeFilterRegistry()

filters_imports = find_n_import("report_filters_register", ['to_register'])
for filter_import in filters_imports:
    report_filters_registry.register(*filter_import.to_register)

#debug('Report: backend registering')
#for app in settings.INSTALLED_APPS:
#    try:
#        find_module("report_backend_register", __import__(app, {}, {}, [app.split(".")[-1]]).__path__)
#    except ImportError, e:
#        # there is no app report_backend_register.py, skip it
#        continue
#
#    backends_import = __import__("%s.report_backend_register" % app , globals(), locals(), ['to_register'], -1)
#    report_backend_registry.register(*backends_import.to_register)