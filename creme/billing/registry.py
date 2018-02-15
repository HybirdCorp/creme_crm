# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from collections import defaultdict
# from imp import find_module
import logging
# import warnings

# from django.apps import apps
from django.utils.datastructures import OrderedSet


logger = logging.getLogger(__name__)


class Algo(object):
    def generate_number(self, organisation, ct, *args, **kwargs):
        pass


class AlgoRegistry(object):
    def __init__(self):
        self._algos = {}

    def register(self, *to_register):
        algos = self._algos

        for name, algo in to_register:
            if name in algos:
                logger.warning("Duplicate algorithm's id or algo registered twice : %s", name)  # exception instead ???

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

# for app_config in apps.get_app_configs():
#     app_name = app_config.name
#
#     try:
#         find_module("billing_register", __import__(app_name, {}, {}, [app_name.split(".")[-1]]).__path__)
#     except (ImportError, TypeError):
#         # there is no app creme_config.py, skip it
#         continue
#
#     warnings.warn("'billing_register' feature is deprecated ; "
#                   "register your algorithms in your AppConfig instead.",
#                   DeprecationWarning
#                  )
#
#     algos_import = __import__("%s.billing_register" % app_name, globals(), locals(), ['to_register'], -1)
#     algo_registry.register(*algos_import.to_register)


# ------------------------------------------------------------------------------
class RelationTypeConverterRegistry(object):
    """ This registry is used when converting a billing document into another billing document.
    The RelationTypes which ContentType doesn't match after the conversion also have to be
    converted into a compatible one.
    """
    def __init__(self):
        self._registry = defaultdict(dict)

    def generate_key(self, source, target):
        return "%s__%s" % (getattr(source, '__name__', source.__class__.__name__),
                           getattr(target, '__name__', target.__class__.__name__))

    def register(self, source_class, initial_relationtype, target_class, final_relationtype):
        key = self.generate_key(source_class, target_class)
        self._registry[key][initial_relationtype] = final_relationtype

    def get_class_map(self, source_object, target_object):
        "Takes instances as arguments"
        return self._registry[self.generate_key(source_object, target_object)]

    def convert_relationtype(self, source_object, target_object, relationtype_id):
        "Takes instances as arguments"
        return self.get_class_map(source_object, target_object).get(relationtype_id, None)


relationtype_converter = RelationTypeConverterRegistry()


# ------------------------------------------------------------------------------
class LinesRegistry(object):
    """ Stores the different Line classes to use with billing document.

    Generally, it is just ProductLine & ServiceLine.
    """
    def __init__(self):
        self._line_classes = OrderedSet()

    def register(self, *classes):
        all_classes = self._line_classes

        for cls in classes:
            all_classes.add(cls)

    # def unregister(self, *classes):
    #     all_classes = self._line_classes
    #
    #     for cls in classes:
    #         try:
    #             all_classes.remove(cls)
    #         except KeyError:
    #             logger.warning("This Line class is not registered : %s", cls)

    def __iter__(self):
        return iter(self._line_classes)


lines_registry = LinesRegistry()
