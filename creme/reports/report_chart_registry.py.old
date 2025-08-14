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

from __future__ import annotations

from collections.abc import Iterator


class ReportChart:
    # def __init__(self, name: str, label: str, template: str | None = None):
    def __init__(self, name: str, label: str):
        self.name = name
        self.label = label
        # self.template: str = template or f'reports/plot/{name}.json'

    def props(self, graph, data):
        return {}


class ReportBarChart(ReportChart):
    # template = 'reports/plot/barchart.json'

    def props(self, graph, data):
        return {
            "xAxisTitle": graph.verbose_abscissa(),
            "yAxisTitle": graph.verbose_ordinate(),
        }


class ReportLineChart(ReportChart):
    def props(self, graph, data):
        return {
            "xAxisTitle": graph.verbose_abscissa(),
            "yAxisTitle": graph.verbose_ordinate(),
        }


class ReportPieChart(ReportChart):
    # template = 'reports/plot/piechart.json'
    pass


class ReportTubeChart(ReportChart):
    # template = 'reports/plot/tubechart.json'

    def props(self, graph, data):
        return {
            "xAxisTitle": graph.verbose_abscissa(),
        }


class ReportChartRegistry:
    __slots__ = ('_charts',)

    def __init__(self) -> None:
        self._charts: dict[str, ReportChart] = {}

    def register(self, *charts: ReportChart) -> ReportChartRegistry:
        for chart in charts:
            self._charts[chart.name] = chart

        return self

    def get(self, name: str) -> ReportChart | None:
        return self._charts.get(name)

    def __iter__(self) -> Iterator[tuple[str, ReportChart]]:
        return iter(self._charts.items())

    def choices(self) -> list[tuple[str, str]]:
        return [(chart.name, chart.label) for chart in self._charts.values()]


report_chart_registry = ReportChartRegistry()
