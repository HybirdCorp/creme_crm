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


# TODO dataclass?
class Plot:
    def __init__(self, name: str, label: str, template: str | None = None):
        self.name = name
        self.label = label
        self.template: str = template or f'reports/plot/{name}.json'

    def props(self, chart, data):
        return {}


class Bar(Plot):
    template = 'reports/plot/barchart.json'

    def props(self, chart, data):
        return {
            'xAxisTitle': chart.verbose_abscissa(),
            'yAxisTitle': chart.verbose_ordinate(),
        }


class Line(Plot):
    def props(self, chart, data):
        return {
            'xAxisTitle': chart.verbose_abscissa(),
            'yAxisTitle': chart.verbose_ordinate(),
        }


class Pie(Plot):
    template = 'reports/plot/piechart.json'


class Tube(Plot):
    template = 'reports/plot/tubechart.json'

    def props(self, chart, data):
        return {
            'xAxisTitle': chart.verbose_abscissa(),
        }


class PlotRegistry:
    __slots__ = ('_plots',)

    _plots: dict[str, Plot]

    def __init__(self):
        self._plots = {}

    def register(self, *plots: Plot) -> PlotRegistry:
        # TODO: check duplicates, empty names...
        for plot in plots:
            self._plots[plot.name] = plot

        return self

    def get(self, name: str) -> Plot | None:
        return self._plots.get(name)

    def __iter__(self) -> Iterator[Plot]:
        yield from self._plots.values()


plot_registry = PlotRegistry()
