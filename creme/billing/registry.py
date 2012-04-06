# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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
from logging import debug, warning

from django.conf import settings


class Algo(object):
    def generate_number(self, organisation, ct, *args, **kwargs):
        pass


class AlgoRegistry(object):
    def __init__(self):
        self._algos = {}

    def register(self, *to_register):
        algos = self._algos

        for name, algo in to_register:
            if algos.has_key(name):
                warning("Duplicate algo's id or algo registered twice : %s", name) #exception instead ???

            algos[name] = algo

    def get_algo(self, name):
        algos = self._algos
        if algos.has_key(name):
            return algos[name]

        return None

    def __iter__(self):
        return self._algos.iteritems()

    def itervalues(self):
        return self._algos.itervalues() 


algo_registry = AlgoRegistry()

#TODO: use creme_core.utils.import find_n_import
debug('Billing: algos registering')
for app in settings.INSTALLED_APPS:
    try:
        find_module("billing_register", __import__(app, {}, {}, [app.split(".")[-1]]).__path__)
    except ImportError, e:
        # there is no app creme_config.py, skip it
        continue

    algos_import = __import__("%s.billing_register" % app , globals(), locals(), ['to_register'], -1)
    algo_registry.register(*algos_import.to_register)
