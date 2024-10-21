################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2024  Hybird
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

# from collections import defaultdict
import warnings

warnings.warn(
    'The module "billing.registry" is deprecated.', DeprecationWarning,
)

# Number algorithms ------------------------------------------------------------
# class Algo:
#     def generate_number(self, organisation, ct, *args, **kwargs):
#         pass
#
#
# class AlgoRegistry:
#     class RegistrationError(Exception):
#         pass
#
#     def __init__(self):
#         self._algos = {}
#
#     def register(self, *to_register):
#         algos = self._algos
#
#         for name, algo in to_register:
#             if name in algos:
#                 raise self.RegistrationError(
#                     f"Duplicated algorithm's id or algorithm registered twice : {name}"
#                 )
#
#             algos[name] = algo
#
#     def get_algo(self, name):
#         return self._algos.get(name)
#
#     def __iter__(self):
#         return iter(self._algos.items())
#
#     @property
#     def algorithms(self):
#         return iter(self._algos.values())
#
#
# algo_registry = AlgoRegistry()


# Conversion -------------------------------------------------------------------
# class RelationTypeConverterRegistry:
#     """ This registry is used when converting a billing document into another billing document.
#     The RelationTypes which ContentType doesn't match after the conversion also have to be
#     converted into a compatible one.
#     """
#     def __init__(self):
#         self._registry = defaultdict(dict)
#
#     def generate_key(self, source, target):
#         return '{}__{}'.format(getattr(source, '__name__', source.__class__.__name__),
#                                getattr(target, '__name__', target.__class__.__name__))
#
#     def register(self, source_class, initial_relationtype, target_class, final_relationtype):
#         key = self.generate_key(source_class, target_class)
#         self._registry[key][initial_relationtype] = final_relationtype
#
#     def get_class_map(self, source_object, target_object):
#         "Takes instances as arguments"
#         return self._registry[self.generate_key(source_object, target_object)]
#
#     def convert_relationtype(self, source_object, target_object, relationtype_id):
#         "Takes instances as arguments"
#         return self.get_class_map(source_object, target_object).get(relationtype_id, None)
#
#
# relationtype_converter = RelationTypeConverterRegistry()


# Lines ------------------------------------------------------------------------
# class LinesRegistry:
#   ...
#
# lines_registry = LinesRegistry()


def __getattr__(name):
    if name == 'LinesRegistry':
        from .core import line

        warnings.warn(
            '"LinesRegistry" is deprecated; use "core.line.LineRegistry" instead.',
            DeprecationWarning,
        )
        return line.LineRegistry

    if name == 'lines_registry':
        from .core import line

        warnings.warn(
            '"lines_registry" is deprecated; use "core.line.line_registry" instead.',
            DeprecationWarning,
        )
        return line.line_registry

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
