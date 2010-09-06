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

from django.db.models.query_utils import Q


class FunctionField(object):
    """A FunctionField is related to a model and represents a special method of
    this model : it has a verbose name and can be used by HeaderFilter to build
    a column (like regular fields).
    """
    name         = "" #name of the attr if the related model class
    verbose_name = "" #verbose name (used by HeaderFilter)
    has_filter   = False #see HeaderFilterItem.has_a_filter

    @classmethod
    def filter_in_result(cls, search_string):
        return Q()

    #@classmethod
    #def execute(cls, obj):
        #return getattr(obj, cls.name)()

    @classmethod
    def populate_entities(cls, entities):
        """Optimisation used for listviews ; see HeaderFilter"""
        pass


class FunctionFieldsManager(object):
    def __init__(self, *function_fields):
        self._function_fields = dict((f_field.name, f_field) for f_field in function_fields)

    def new(self, *function_fields):
        all_fields = self._function_fields.values()
        all_fields.extend(function_fields)

        return FunctionFieldsManager(*all_fields)

    def __iter__(self):
        return self._function_fields.itervalues()

    def get(self, name):
        return self._function_fields.get(name)
