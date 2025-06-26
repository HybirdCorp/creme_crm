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

from collections.abc import Iterable, Iterator, Sequence

from ..backends.gui import BrickHeaderAction, TemplateBrickHeaderAction
from ..backends.models import CrudityBackend


class CrudityInput:
    name   = ''
    method = ''

    verbose_name   = ''
    verbose_method = ''

    brickheader_action_templates: Sequence[str] = ()

    def __init__(self) -> None:
        self._backends: dict[str, CrudityBackend] = {}
        self._brickheader_actions: list[BrickHeaderAction] = [
            TemplateBrickHeaderAction(template_name=tn)
            for tn in self.brickheader_action_templates
        ]

    def add_backend(self, backend: CrudityBackend) -> None:
        self._backends[backend.subject] = backend

    # TODO: rename 'backends' + property + generator ?
    def get_backends(self) -> list[CrudityBackend]:
        return [*self._backends.values()]

    def get_backend(self, subject: str) -> CrudityBackend | None:
        return self._backends.get(subject)

    @property
    def has_backends(self) -> bool:
        return bool(self._backends)

    def handle(self, data) -> CrudityBackend | None:
        """Call the method of the Input defined in subclasses.
        @return: The backend used if data were used else None.
        """
        fun = getattr(self, self.method, None)
        if fun:
            return fun(data)

        return None

    @property
    def brickheader_actions(self) -> Iterator[BrickHeaderAction]:
        return iter(self._brickheader_actions)

    def authorize_senders(self, backend: CrudityBackend, senders: Iterable[str]) -> bool:
        return bool(not backend.limit_froms or ({*senders} & {*backend.limit_froms}))
