# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

import logging
from collections import defaultdict
from copy import deepcopy
from typing import (
    Any,
    DefaultDict,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Type,
)

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.serializers.base import DeserializationError
from django.core.serializers.python import _get_model

from creme.creme_core.models import CremeEntity
from creme.creme_core.utils.collections import OrderedSet
from creme.creme_core.utils.imports import import_apps_sub_modules

from .backends.models import CrudityBackend
from .fetchers.base import CrudityFetcher
from .inputs.base import CrudityInput

logger = logging.getLogger(__name__)
ALLOWED_ID_CHARS = OrderedSet(
    'abcdefghijklmnopqrstuvwxyz'
    'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.'
)


class FetcherInterface:
    """Multiple fetchers of the same "type" (i.e: pop email, imap email...) could
    be registered with the same key in CRUDityRegistry.
    FetcherInterface abstract those to act like one fetcher.
    """
    fetchers: List[CrudityFetcher]
    _inputs: DefaultDict[str, Dict[str, CrudityInput]]
    _default_backend: Optional[CrudityBackend]

    def __init__(self, fetchers: Iterable[CrudityFetcher]):
        self.fetchers = [*fetchers]
        self._inputs = defaultdict(dict)
        self._default_backend = None

    def add_fetchers(self, fetchers: Iterable[CrudityFetcher]) -> None:
        self.fetchers.extend(fetchers)

    def add_inputs(self, *inputs: CrudityInput) -> None:
        for crud_input in inputs:
            self._inputs[crud_input.name][crud_input.method] = crud_input

    def get_input(self, name: str, method: str) -> Optional[CrudityInput]:
        input_name = self._inputs.get(name)
        if input_name is not None:
            return input_name.get(method)

        return None

    def get_inputs(self) -> Iterator[Dict[str, CrudityInput]]:
        return iter(self._inputs.values())

    def fetch(self) -> list:
        data: list = []

        for fetcher in self.fetchers:
            data.extend(fetcher.fetch())

        return data

    def get_default_backend(self) -> Optional[CrudityBackend]:
        """Special case, for retrieving the backend defined as the default one.
        The backend should be aware in his fetcher_fallback method that the input
        is not a dict of data but the raw data
        (i.e: An email object for the backend defined as the fallback of the email fetcher)
        To set a backend as the fallback the subject has to be fetcher_name/*
        """
        return self._default_backend

    def register_default_backend(self, backend: CrudityBackend) -> None:
        self._default_backend = backend


class CRUDityRegistry:
    class RegistrationError(Exception):
        pass

    def __init__(self):
        self._fetchers: Dict[str, FetcherInterface] = {}
        self._backends: Dict[Type[CremeEntity], Type[CrudityBackend]] = {}

    def __str__(self):
        res = 'CRUDityRegistry:'

        for fetcher_name, fetcher_interface in self._fetchers.items():
            res += '\n - Fetcher("{}"): {}'.format(
                fetcher_name,
                '/'.join(fetcher.__class__.__name__ for fetcher in fetcher_interface.fetchers),
            )

            default_backend = fetcher_interface.get_default_backend()
            if default_backend:
                res += f'    Default backend: {default_backend}'

            for input_name, inputs in fetcher_interface._inputs.items():
                res += f'\n    - Input("{input_name}"):'

                for method, input in inputs.items():
                    res += f'\n       - Method "{method}": <{input.__class__.__name__}>'

                    backends = input.backends

                    if not backends:
                        res += ' -> No BACKEND'
                    else:
                        res += '\n         Backends:'
                        for subject, backend in input.backends.items():
                            res += f'\n          - {subject}: {backend.__class__.__name__}'

        return res

    def autodiscover(self):
        for crud_import in import_apps_sub_modules('crudity_register'):
            # Fetchers
            fetchers = getattr(crud_import, 'fetchers', {})
            register_fetchers = self.register_fetchers
            for source_type, fetchers_classes in fetchers.items():
                if any(c not in ALLOWED_ID_CHARS for c in source_type):
                    raise ValueError(
                        'The fetchers ID "{}" (in {}) use forbidden characters '
                        '[allowed ones: {}].'.format(
                            source_type, crud_import, ''.join(ALLOWED_ID_CHARS),
                        )
                    )

                register_fetchers(source_type, [fetcher_cls() for fetcher_cls in fetchers_classes])

            # Inputs
            inputs = getattr(crud_import, 'inputs', {})
            register_inputs = self.register_inputs
            for source_type, input_classes in inputs.items():
                for crud_input in input_classes:
                    if any(c not in ALLOWED_ID_CHARS for c in crud_input.name):
                        raise ValueError(
                            'The input ID "{}" ({}) use forbidden characters '
                            '[allowed ones: {}].'.format(
                                crud_input.name, crud_input.__class__, ''.join(ALLOWED_ID_CHARS),
                            )
                        )

                register_inputs(source_type, [input_cls() for input_cls in input_classes])

            # Backends (registered by models)
            backends = getattr(crud_import, 'backends', [])
            self.register_backends(backends)

    def register_fetchers(self, source: str, fetchers: List[CrudityFetcher]) -> None:
        fetcher_multiplex = self._fetchers.get(source)

        # TODO: defaultdict...
        if fetcher_multiplex is None:
            self._fetchers[source] = FetcherInterface(fetchers)
        else:
            fetcher_multiplex.add_fetchers(fetchers)

    def get_fetchers(self) -> List[FetcherInterface]:  # TODO: iterator instead
        return [*self._fetchers.values()]

    def get_fetcher(self, source: str) -> Optional[FetcherInterface]:
        return self._fetchers.get(source)

    def register_inputs(self,
                        source: str,
                        inputs: List[CrudityInput],
                        ) -> None:
        fetcher = self.get_fetcher(source)

        if fetcher is not None:
            fetcher.add_inputs(*inputs)
        else:
            logger.warning(
                "The fetcher '%s' does not exist, inputs '%s' will not be registered",
                source, inputs,
            )

    def register_backends(self, backends: Iterable[Type[CrudityBackend]]) -> None:
        for backend in backends:
            # TODO: error if model is already associated with the model ?
            #       (or a log in order to override cleanly)
            self._backends[backend.model] = backend

    def get_backends(self) -> Iterator[Type[CrudityBackend]]:  # TODO: rename ?
        """Get all registered backend
         @returns: An iterator of backend classes.
        """
        return iter(self._backends.values())

    def get_backend(self, model: Type[CremeEntity]) -> Type[CrudityBackend]:  # TODO: remove ?
        """Get the registered backend class for the model"""
        try:
            return self._backends[model]
        except KeyError as e:
            raise self.RegistrationError(
                f'No backend is registered for the model "{model}"'
            ) from e

    def get_configured_backends(self) -> List[CrudityBackend]:
        """Get backends instances which are configured and associated to an input
        (which is itself linked to a fetcher).
        @return: A list of configured backend instances
        """
        backends = []

        for fetcher in self.get_fetchers():
            for crud_inputs in fetcher.get_inputs():
                for crud_input in crud_inputs.values():
                    backends.extend(crud_input.get_backends())

            default_be = fetcher.get_default_backend()

            if default_be is not None:
                backends.append(default_be)

        return backends

    def get_configured_backend(self,
                               fetcher_name: str,
                               input_name: str,
                               norm_subject: str,
                               ) -> CrudityBackend:
        try:
            fetcher = self._fetchers[fetcher_name]
        except KeyError as e:
            raise KeyError('Fetcher not found: ' + fetcher_name) from e

        try:
            crud_inputs = fetcher._inputs[input_name]  # TODO: FetcherInterface method ?
        except KeyError as e:
            raise KeyError('Input not found: ' + input_name) from e

        for crud_input in crud_inputs.values():
            backend = crud_input.get_backend(norm_subject)

            if backend:
                return backend

        raise KeyError('Backend not found: ' + norm_subject)

    def get_default_backend(self, fetcher_name: str) -> CrudityBackend:
        # fetcher = crudity_registry.get_fetcher(fetcher_name)
        fetcher = self.get_fetcher(fetcher_name)
        if not fetcher:
            raise KeyError(f'Unknown fetcher "{fetcher_name}"')

        backend = fetcher.get_default_backend()
        if not backend:
            raise KeyError(f'Fetcher "{fetcher_name}" has no default backend')

        return backend

    def dispatch(self, backend_configs: List[Dict[str, Any]]) -> None:
        for backend_cfg in backend_configs:
            backend_cfg = deepcopy(backend_cfg)

            try:
                fetcher_source = backend_cfg.pop('fetcher')
                input_name     = backend_cfg.pop('input', '')
                # TODO: use ContentType.objects.get_by_natural_key() ?
                # TODO: accept swappable ID ?
                model          = _get_model(backend_cfg.pop('model'))
                method         = backend_cfg.pop('method', '')
                subject        = backend_cfg['subject']
            except KeyError as e:
                raise ImproperlyConfigured(
                    f'You have an error in your CRUDITY_BACKENDS settings. '
                    f'Check if "{e}" is present'
                ) from e
            except DeserializationError as de:
                raise ImproperlyConfigured(de) from de
            else:
                backend_cls = self._backends.get(model)
                if backend_cls is None:
                    raise ImproperlyConfigured(
                        f'settings.CRUDITY_BACKENDS: '
                        f'no backend is registered for this model <{model}>'
                    )

                fetcher = self.get_fetcher(fetcher_source)

                if fetcher is None:
                    raise ImproperlyConfigured(
                        f'settings.CRUDITY_BACKENDS: invalid fetcher "{fetcher_source}".'
                    )

                if subject == '*':
                    if fetcher.get_default_backend() is not None:
                        raise ImproperlyConfigured(
                            f'settings.CRUDITY_BACKENDS: '
                            f'only one fallback backend is allowed for '
                            f'"{fetcher_source}/{input_name}".'
                        )

                    backend_cfg['source'] = fetcher_source
                    backend_instance = backend_cls(backend_cfg)

                    if not hasattr(backend_instance, 'fetcher_fallback'):
                        raise ImproperlyConfigured(
                            f'settings.CRUDITY_BACKENDS: '
                            f'the backend for "{model}" cannot be used as fallback '
                            f'(ie: subject="*").'
                        )

                    backend_instance.fetcher_name = fetcher_source

                    fetcher.register_default_backend(backend_instance)
                else:
                    if not input_name:
                        raise ImproperlyConfigured(
                            f'settings.CRUDITY_BACKENDS: '
                            f'you have to declare an input for the fetcher {fetcher_source}.'
                        )

                    if not method:
                        raise ImproperlyConfigured(
                            f'settings.CRUDITY_BACKENDS: '
                            f'you have to declare a method for "{fetcher_source}/{input_name}".'
                        )

                    crud_input = fetcher.get_input(input_name, method)

                    if not crud_input:
                        raise ImproperlyConfigured(
                            f'settings.CRUDITY_BACKENDS: '
                            f'invalid input "{input_name}" for the fetcher "{fetcher_source}".'
                        )

                    # TODO: move this code to backend
                    backend_cfg['source'] = f'{fetcher_source} - {input_name}'
                    backend_cfg['verbose_source'] = crud_input.verbose_name  # For i18n
                    backend_cfg['verbose_method'] = crud_input.verbose_method  # For i18n

                    backend_instance = backend_cls(backend_cfg, crud_input=crud_input)
                    backend_instance.fetcher_name = fetcher_source
                    backend_instance.input_name = input_name

                    if crud_input.get_backend(backend_instance.subject):
                        raise ImproperlyConfigured(
                            f'settings.CRUDITY_BACKENDS: '
                            f'this (normalised) subject must be unique for '
                            f'"{fetcher_source}/{input_name}": {backend_instance.subject}'
                        )

                    crud_input.add_backend(backend_instance)

    def fetch(self, user) -> List[CrudityBackend]:
        used_backends = []

        def _handle_data(multi_fetcher: FetcherInterface, data) -> Optional[CrudityBackend]:
            for inputs_per_method in multi_fetcher.get_inputs():
                for crud_input in inputs_per_method.values():
                    handling_backend = crud_input.handle(data)

                    if handling_backend is not None:
                        return handling_backend

                default_backend = multi_fetcher.get_default_backend()

                if default_backend is not None:
                    # TODO: need better type for default backend (fetcher_fallback() method)
                    default_backend.fetcher_fallback(data, user)
                    return default_backend

            return None

        for fetcher_multiplex in self.get_fetchers():
            # TODO: FetcherInterface.has_backends() ?
            if not any(
                crud_input.has_backends
                for inputs_per_method in fetcher_multiplex.get_inputs()
                for crud_input in inputs_per_method.values()
            ) and not fetcher_multiplex.get_default_backend():
                continue

            for data in fetcher_multiplex.fetch():
                backend = _handle_data(fetcher_multiplex, data)

                if backend:
                    used_backends.append(backend)

        return used_backends


crudity_registry = CRUDityRegistry()
crudity_registry.autodiscover()
crudity_registry.dispatch(settings.CRUDITY_BACKENDS)
