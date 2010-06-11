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

from sys import modules
from bisect import insort

from django.db import connection
from django.conf import settings


class LogImportedModulesMiddleware(object):
    def process_response(self, request, response):
        if connection.queries:
            prefix = 'creme.'
            pl = len(prefix)
            creme_app_names = frozenset(app[pl:] for app in settings.INSTALLED_APPS if app.startswith(prefix))

            outputs = []
            modules_set = set()

            for module_name, module_obj in modules.iteritems():
                if not module_obj:
                    continue

                if module_name.startswith(prefix):
                    module_name = module_name[pl:]

                if module_name in modules_set:
                    continue

                app, sep, subapp = module_name.partition('.')

                if app in creme_app_names:
                    insort(outputs, module_name)
                    modules_set.add(module_name)

            print 'IMPORTED MODULES:', len(outputs), 'module(s)'
            for output in outputs:
                print '  -', output

        return response
