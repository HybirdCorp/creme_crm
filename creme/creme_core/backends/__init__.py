################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2025  Hybird
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

# TODO: move to 'core/' ??

from collections.abc import Iterable, Iterator
from typing import Generic, TypeVar

from django.conf import settings

from creme.creme_core.utils.imports import safe_import_object

from . import base

BackendBaseClass = TypeVar('BackendBaseClass')


class _BackendRegistry(Generic[BackendBaseClass]):
    class InvalidClass(Exception):
        pass

    class DuplicatedId(Exception):
        pass

    def __init__(self,
                 base_backend_class: type[BackendBaseClass],
                 settings: Iterable[str],
                 ):
        self._backend_classes: dict[str, type[BackendBaseClass]] | None = None
        self._settings: list[str] = [*settings]
        self._base_backend_class = base_backend_class

    def _get_backend_classes(self) -> dict[str, type[BackendBaseClass]]:
        if self._backend_classes is None:
            backends: dict[str, type[BackendBaseClass]] = {}
            base_cls = self._base_backend_class

            for backend in self._settings:
                BackendClass = safe_import_object(backend)
                if BackendClass is None:  # safe_import_object logged and Exception
                    continue

                if not issubclass(BackendClass, base_cls):
                    raise self.InvalidClass(
                        f'Backend: {BackendClass} is invalid, it is not a sub-class of {base_cls}.'
                    )

                backend_id = BackendClass.id

                if backend_id in backends:
                    raise self.DuplicatedId(
                        'Id: {backend_id} already used for {backends[backend_id]}. '
                        'Please specify another id for {BackendClass}.'
                    )

                backends[backend_id] = BackendClass

            self._backend_classes = backends

        return self._backend_classes

    def __bool__(self):
        return bool(self._get_backend_classes())

    @property
    def backend_classes(self) -> Iterator[type[BackendBaseClass]]:
        return iter(self._get_backend_classes().values())

    @property
    def extensions(self) -> Iterator[str]:
        return iter(self._get_backend_classes().keys())

    def get_backend_class(self, backend_id: str) -> type[BackendBaseClass] | None:
        return self._get_backend_classes().get(backend_id)


import_backend_registry = _BackendRegistry(base.ImportBackend, settings.IMPORT_BACKENDS)
# TODO: specific registry class with a get_backend() method which returns an instance
export_backend_registry = _BackendRegistry(base.ExportBackend, settings.EXPORT_BACKENDS)
