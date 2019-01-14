# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2018  Hybird
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
# import warnings

from django.conf import settings

from creme.creme_core.utils.imports import safe_import_object


class _BackendRegistry:
    class InvalidId(Exception):
        pass

    class DuplicatedId(Exception):
        pass

    def __init__(self, settings):
        self._backends = None
        self._settings = settings

    def _get_backends(self):
        if self._backends is None:
            backends = {}

            for backend in self._settings:
                BackendClass = safe_import_object(backend)
                if BackendClass is None:  # safe_import_object logged and Exception
                    continue

                backend_id = getattr(BackendClass, 'id', None)
                if backend_id is None:
                    raise self.InvalidId('Backend: {} has invalid id.'.format(BackendClass))

                if backend_id in backends:
                    raise self.DuplicatedId('Id: {} already used for {}. Please specify another id for {}'.format(
                                    backend_id, backends[backend_id], BackendClass
                    ))

                backends[backend_id] = BackendClass

            self._backends = backends

        return self._backends

    @property
    def backends(self):
        return iter(self._get_backends().values())

    # def iterbackends(self):
    #     warnings.warn('_BackendRegistry.iterbackends() is deprecated ; '
    #                   'use _BackendRegistry.backends instead.',
    #                   DeprecationWarning
    #                  )
    #
    #     return self.backends

    @property
    def extensions(self):
        return self._get_backends().keys()

    # def iterkeys(self):
    #     warnings.warn('_BackendRegistry.iterkeys() is deprecated ; '
    #                   'use _BackendRegistry.extensions instead.',
    #                   DeprecationWarning
    #                  )
    #
    #     return self.extensions

    def get_backend(self, backend_id):
        return self._get_backends().get(backend_id)


import_backend_registry = _BackendRegistry(settings.IMPORT_BACKENDS)
export_backend_registry = _BackendRegistry(settings.EXPORT_BACKENDS)
