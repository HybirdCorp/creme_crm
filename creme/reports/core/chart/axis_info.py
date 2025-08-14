################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2020-2025  Hybird
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

from typing import Any

from creme.creme_core.core.entity_cell import EntityCell


class AbscissaInfo:
    def __init__(self,
                 cell: EntityCell | None,
                 chart_type: int,  # See constants.AbscissaGroup  # TODO: group_id??
                 parameter: Any | None = None,
                 ):
        self.cell = cell
        self.chart_type = chart_type
        self.parameter = parameter

    def __repr__(self):
        return (
            f'AbscissaInfo('
            f'cell=<{self.cell}>, '
            f'chart_type={self.chart_type}, '
            f'parameter={self.parameter}'
            f')'
        )


class OrdinateInfo:
    def __init__(self,
                 aggr_id: str,  # See constants.OrdinateAggregator
                 cell: EntityCell | None = None,
                 ):
        self.aggr_id = aggr_id
        self.cell = cell

    def __repr__(self):
        return f'OrdinateInfo(cell=<{self.cell}>, aggr_id="{self.aggr_id}")'
