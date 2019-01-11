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

# import warnings

from django.db import models
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.models import CustomField


class FieldAggregation:
    def __init__(self, name, func, pattern, title):
        self.name    = name
        self.func    = func
        self.pattern = pattern
        self.title   = title


class FieldAggregationRegistry:
    __slots__ = ('_aggregations',)

    authorized_fields = (models.DecimalField, models.FloatField, models.PositiveIntegerField,
                         models.PositiveSmallIntegerField, models.IntegerField, models.SmallIntegerField,
                        )
    authorized_customfields = (CustomField.INT, CustomField.FLOAT)

    def __init__(self):
        self._aggregations = {}

    def register(self, name, field_aggregation):
        self._aggregations[name] = field_aggregation

    def get(self, name):
        return self._aggregations.get(name)

    def __iter__(self):
        return self._aggregations.items()

    @property
    def aggregations(self):
        return iter(self._aggregations.values())

    # def itervalues(self):
    #     warnings.warn('FieldAggregationRegistry.itervalues() is deprecated ; '
    #                   'use FieldAggregationRegistry.aggregations instead.',
    #                   DeprecationWarning
    #                  )
    #
    #     return self.aggregations


field_aggregation_registry = FieldAggregationRegistry()
field_aggregation_registry.register('avg', FieldAggregation('avg', models.Avg, '{}__avg', _(u'Average')))
field_aggregation_registry.register('min', FieldAggregation('min', models.Min, '{}__min', _(u'Minimum')))
field_aggregation_registry.register('max', FieldAggregation('max', models.Max, '{}__max', _(u'Maximum')))
field_aggregation_registry.register('sum', FieldAggregation('sum', models.Sum, '{}__sum', _(u'Sum')))
