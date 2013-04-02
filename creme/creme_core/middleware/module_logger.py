# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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


class LogImportedModulesMiddleware(object):
    def process_response(self, request, response):
        if connection.queries:
            outputs = []

            for module_name, module_obj in modules.iteritems():
                if not module_obj:
                    continue

                if not module_name.startswith('creme.'):
                    continue

                insort(outputs, module_name)

            print 'IMPORTED MODULES:', len(outputs), 'module(s)'
            for output in outputs:
                print '  -', output

        return response
