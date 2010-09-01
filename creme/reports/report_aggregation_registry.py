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

from django.db.models import Avg, Min, Max, Sum
from django.utils.translation import ugettext_lazy as _
from django.db import models


class FieldAggregation(object):
    def __init__(self, name, func, pattern, title):
        self.name    = name
        self.func    = func
        self.pattern = pattern
        self.title   = title

class FieldAggregationRegistry(object):

    authorized_fields = [models.DecimalField, models.FloatField, models.PositiveIntegerField,
                         models.PositiveSmallIntegerField, models.IntegerField, models.SmallIntegerField, ]

    def __init__(self):
        self._aggregations = {}

    def register(self, name, field_aggregation):
        self._aggregations[name] = field_aggregation

    def get(self, name):
        return self._aggregations.get(name)

    def __iter__(self):
        return self._aggregations.iteritems()

    def itervalues(self):
        return self._aggregations.itervalues()

field_aggregation_registry = FieldAggregationRegistry()
field_aggregation_registry.register('avg', FieldAggregation('avg', Avg, '%s__avg', _(u'Average')))
field_aggregation_registry.register('min', FieldAggregation('min', Min, '%s__min', _(u'Minimum')))
field_aggregation_registry.register('max', FieldAggregation('max', Max, '%s__max', _(u'Maximum')))
field_aggregation_registry.register('sum', FieldAggregation('sum', Sum, '%s__sum', _(u'Sum')))
