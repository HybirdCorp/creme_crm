# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2020  Hybird
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

from typing import Any, Optional

from creme.creme_core.core.entity_cell import EntityCell


class AbscissaInfo:
    def __init__(self,
                 cell: EntityCell,
                 graph_type: int,
                 parameter: Optional[Any] = None):
        self.cell = cell
        self.graph_type = graph_type
        self.parameter = parameter

    def __repr__(self):
        return (
            f'AbscissaInfo(cell=<{self.cell}>, '
                         f'graph_type={self.graph_type}, '
                         f'parameter={self.parameter})'
        )
