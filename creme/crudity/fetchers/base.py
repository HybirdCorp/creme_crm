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

from collections import defaultdict
from collections.abc import Iterable
from typing import DefaultDict

from ..inputs.base import CrudityInput


class CrudityFetcher:
    _inputs: DefaultDict[str, dict[str, CrudityInput]]

    def __init__(self, *args, **kwargs):
        self._inputs = defaultdict(dict)

    def register_inputs(self, *inputs: CrudityInput) -> None:
        for input in inputs:
            self._inputs[input.name][input.method] = input

    def fetch(self, *args, **kwargs) -> Iterable:
        """Make the fetcher do his job.
        @returns: iterable of fetcher managed type
                  (i.e: emails objects for email fetcher for example).
        """
        raise NotImplementedError
