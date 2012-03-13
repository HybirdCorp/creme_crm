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

from django.db.models.query_utils import Q
from django.utils.html import escape


class FunctionField(object):
    """A FunctionField is related to a model and represents a special method of
    this model : it has a verbose name and can be used by HeaderFilter to build
    a column (like regular fields).
    """
    name         = "" #name of the attr if the related model class
    verbose_name = "" #verbose name (used by HeaderFilter)
    has_filter   = False #see HeaderFilterItem.has_a_filter
    is_hidden    = False #see HeaderFilterItem.is_hidden
    choices      = None #Choices for list_view filtering. Has to be like django choices (e.g: [(1, 'First choice', ...), ] )

    @classmethod
    def filter_in_result(cls, search_string):
        return Q()

    def __call__(self, entity):
        """"@return An instance of FunctionField object
        (so you can call for_html()/for_csv() on the result)."""
        return FunctionFieldResult(getattr(entity, self.name)())

    @classmethod
    def populate_entities(cls, entities):
        """Optimisation used for listviews ; see HeaderFilter"""
        pass


class FunctionFieldResult(object):
    __slots__ = ('_data',)

    def __init__(self, str_data):
        self._data = str_data

    def __unicode__(self, str_data):
        return self.for_html()

    def for_html(self):
        return escape(self._data)

    def for_csv(self):
        return self._data


class FunctionFieldResultsList(FunctionFieldResult):
    def __init__(self, iterable):
        self._data = list(iterable)

    def for_html(self):
        return u"<ul>%s</ul>" % u"".join(u"<li>%s</li>" % e.for_html() for e in self._data)

    def for_csv(self):
        return u"/".join(e.for_csv() for e in self._data)


class FunctionFieldsManager(object):
    def __init__(self, *function_fields):
        self._function_fields = dict((f_field.name, f_field) for f_field in function_fields)
        self._parent = None

    def __iter__(self):
        manager = self

        while manager:
            for func_field in manager._function_fields.itervalues():
                yield func_field

            manager = manager._parent

    def add(self, *function_fields):
        self._function_fields.update((f_field.name, f_field) for f_field in function_fields)

    def get(self, name):
        func_field = self._function_fields.get(name)

        if not func_field and self._parent:
            func_field = self._parent.get(name)

        return func_field

    def new(self, *function_fields):
        """Use this method when you inherit a class, and you want to add new
        function fields to the inherited class, but not to the base class.
        """
        ffm = FunctionFieldsManager(*function_fields)
        ffm._parent = self

        return ffm
