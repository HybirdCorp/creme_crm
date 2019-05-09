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

from django.utils.translation import gettext_lazy as _


class ReportChart:
    def __init__(self, name, label, template=None):
        self.name = name
        self.label = label
        self.template = template or 'reports/plot/{}.json'.format(name)


class ReportChartRegistry:
    __slots__ = ('_charts',)

    def __init__(self):
        self._charts = {}

    def register(self, chart):
        self._charts[chart.name] = chart
        return self

    def get(self, name):
        return self._charts.get(name)

    def __iter__(self):
        return iter(self._charts.items())

    def choices(self):
        return [(chart.name, chart.label) for chart in self._charts.values()]


report_chart_registry = ReportChartRegistry()
report_chart_registry.register(ReportChart('barchart',  _('Histogram'))) \
                     .register(ReportChart('piechart',  _('Pie'))) \
                     .register(ReportChart('tubechart', _('Tube')))
