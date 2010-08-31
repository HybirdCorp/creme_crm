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
from logging import debug

from django.conf import settings

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

debug('Report: backend registering')
for app in settings.INSTALLED_APPS:
    try:
        find_module("report_backend_register", __import__(app, {}, {}, [app.split(".")[-1]]).__path__)
    except ImportError, e:
        # there is no app report_backend_register.py, skip it
        continue

    backends_import = __import__("%s.report_backend_register" % app , globals(), locals(), ['to_register'], -1)
    report_backend_registry.register(*backends_import.to_register)