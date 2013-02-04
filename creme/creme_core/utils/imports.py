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

from django.conf import settings


def find_n_import(filename, imports):
    results = []

    for app in settings.INSTALLED_APPS:
        try:
            find_module(filename, __import__(app, {}, {}, [app.split(".")[-1]]).__path__)
        except ImportError:
            # there is no app report_backend_register.py, skip it
            continue

        results.append(__import__("%s.%s" % (app, filename) , globals(), locals(), imports, -1))

    return results
