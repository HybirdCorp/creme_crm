################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

# TODO: move this module to reports.core?
from __future__ import annotations

from collections.abc import Iterator

from django.db import models
from django.db.models.aggregates import Aggregate

from creme.creme_core.models import CustomField


class FieldAggregation:
    def __init__(self, name: str, func: type[Aggregate], pattern: str, title: str):
        self.name = name
        self.func = func
        self.pattern = pattern
        self.title = title


class FieldAggregationRegistry:
    __slots__ = ('_aggregations',)

    authorized_fields: tuple[type[models.Field], ...] = (
        models.IntegerField,
        models.DecimalField,
        models.FloatField,
    )

    def __init__(self) -> None:
        self._aggregations: dict[str, FieldAggregation] = {}

    def register(self, field_aggregation: FieldAggregation) -> FieldAggregationRegistry:
        """Register a type of aggregation for reports.
        @param field_aggregation: Instance of FieldAggregation.
        @return A reference to self, to allow fluent chaining of 'register()' calls.
        """
        self._aggregations[field_aggregation.name] = field_aggregation
        return self

    def get(self, name: str) -> FieldAggregation | None:
        return self._aggregations.get(name)

    @property
    def aggregations(self) -> Iterator[FieldAggregation]:
        return iter(self._aggregations.values())

    def is_custom_field_allowed(self, custom_field: CustomField):
        return isinstance(
            custom_field.value_class._meta.get_field('value'),
            self.authorized_fields,
        )

    def is_regular_field_allowed(self, field: models.Field):
        return isinstance(field, self.authorized_fields)


field_aggregation_registry = FieldAggregationRegistry()
