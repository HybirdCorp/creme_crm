################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024-2025  Hybird
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

from contextlib import ContextDecorator

from ..global_info import get_per_request_cache
from ..models.history import HISTORY_ENABLED_CACHE_KEY, is_history_enabled


def do_toggle_history(*, enabled: bool) -> None:
    """ Function designed to enable or disable history.
    Hint: you should use toggle_history() instead whenever it's possible.

    Usages:

    def do_something():
        toggle_history(enabled=False)
        ...
        toggle_history(enabled=True)

    @param enabled: True to enable history, False to disable.
    """
    get_per_request_cache()[HISTORY_ENABLED_CACHE_KEY] = enabled


class toggle_history(ContextDecorator):
    """ Decorator and context manager designed to enable or disable history.

    Usages:

    @toggle_history(enabled=False)
    def do_something():
        do()

    or

    with toggle_history(enabled=False):
        do_something()
    """
    def __init__(self, *, enabled: bool) -> None:
        self.enabled = enabled

    def __enter__(self):
        self.initial = is_history_enabled()
        do_toggle_history(enabled=self.enabled)

    def __exit__(self, *exc):
        do_toggle_history(enabled=self.initial)

        return False  # Exceptions are not captured
