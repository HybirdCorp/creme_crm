################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2026  Hybird
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


class ExpandableLine:
    """Store a line of report values that can be expanded in several lines if
    there are selected sub-reports.
    """
    def __init__(self, values: list[str | list]):
        self._cvalues = values

    def _visit(self, lines: list, current_line: list) -> None:
        values: list[str | None] = []
        values_to_build = None

        for col_value in self._cvalues:
            if isinstance(col_value, list):
                values.append(None)
                values_to_build = col_value
            else:
                values.append(col_value)

        if None in current_line:
            idx = current_line.index(None)
            current_line[idx:idx + 1] = values
        else:
            current_line.extend(values)

        if values_to_build is not None:
            cls = type(self)

            for future_node in values_to_build:
                cls(future_node)._visit(lines, [*current_line])
        else:
            lines.append(current_line)

    def get_lines(self) -> list[list[str]]:
        lines: list[list[str]] = []
        self._visit(lines, [])

        return lines
