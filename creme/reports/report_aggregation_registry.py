# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

from django.db import models

from creme.creme_core.models import CustomField


class FieldAggregation:
    def __init__(self, name, func, pattern, title):
        self.name    = name
        self.func    = func
        self.pattern = pattern
        self.title   = title


class FieldAggregationRegistry:
    __slots__ = ('_aggregations',)

    authorized_fields = (
        models.DecimalField, models.FloatField, models.PositiveIntegerField,
        models.PositiveSmallIntegerField, models.IntegerField, models.SmallIntegerField,
    )
    authorized_customfields = (CustomField.INT, CustomField.FLOAT)

    def __init__(self):
        self._aggregations = {}

    def register(self, field_aggregation):
        """Register a type of aggregation for reports.
        @param field_aggregation: Instance of FieldAggregation.
        @return A reference to self, to allow fluent chaining of 'register()' calls.
        """
        self._aggregations[field_aggregation.name] = field_aggregation
        return self

    def get(self, name):
        return self._aggregations.get(name)

    def __iter__(self):
        return self._aggregations.items()

    @property
    def aggregations(self):
        return iter(self._aggregations.values())


field_aggregation_registry = FieldAggregationRegistry()
