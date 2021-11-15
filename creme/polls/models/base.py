# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2012-2021  Hybird
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

from collections import defaultdict


class _PollLine:
    type      = None  # OVERRIDE ME (INT: See PollLineType)
    type_args = None  # OVERRIDE ME (JSON string: See PollLineType)

    _conditions_cache     = None
    _rev_conditions_cache = None
    _line_type_cache      = None

    @classmethod
    def _get_condition_class(cls):
        raise NotImplementedError

    def get_conditions(self):
        if self._conditions_cache is None:
            self._conditions_cache = [*self.conditions.all()]

        return self._conditions_cache

    def get_reversed_conditions(self):
        if self._rev_conditions_cache is None:
            self._rev_conditions_cache = [
                *self._get_condition_class().objects.filter(source=self)
            ]

        return self._rev_conditions_cache

    @property
    def poll_line_type(self):
        # Import here to avoid AppRegistryNotReady
        from ..core import PollLineType

        line_type = self._line_type_cache

        if line_type is None:
            line_type = self._line_type_cache = \
                PollLineType.build_from_serialized_args(self.type, self.type_args)

        return line_type

    @classmethod
    def populate_conditions(cls, lines):
        conditions_map = defaultdict(list)
        rev_conditions_map = defaultdict(list)

        for condition in cls._get_condition_class().objects.filter(
                line__in=[line.id for line in lines],
        ):
            conditions_map[condition.line_id].append(condition)
            rev_conditions_map[condition.source_id].append(condition)

        for line in lines:
            line_id = line.id
            line._conditions_cache     = conditions_map[line_id]
            line._rev_conditions_cache = rev_conditions_map[line_id]
