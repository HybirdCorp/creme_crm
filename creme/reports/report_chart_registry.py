# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

from typing import Dict, Iterator, List, Optional, Tuple


class ReportChart:
    def __init__(self, name: str, label: str, template: Optional[str] = None):
        self.name = name
        self.label = label
        self.template: str = template or f'reports/plot/{name}.json'


class ReportChartRegistry:
    __slots__ = ('_charts',)

    def __init__(self):
        self._charts: Dict[str, ReportChart] = {}

    def register(self, chart: ReportChart) -> 'ReportChartRegistry':
        self._charts[chart.name] = chart
        return self

    def get(self, name: str) -> Optional[ReportChart]:
        return self._charts.get(name)

    def __iter__(self) -> Iterator[Tuple[str, ReportChart]]:
        return iter(self._charts.items())

    def choices(self) -> List[Tuple[str, str]]:
        return [(chart.name, chart.label) for chart in self._charts.values()]


report_chart_registry = ReportChartRegistry()
