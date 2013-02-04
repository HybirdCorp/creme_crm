# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

#from itertools import chain
from logging import warning
from collections import defaultdict

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.serializers.base import DeserializationError
from django.core.serializers.python import _get_model

from creme_core.registry import NotRegistered
from creme_core.utils.imports import find_n_import

from crudity.backends.models import CrudityBackend


class FetcherInterface(object):
    """
    Multiple fetchers of the same "type" (i.e: pop email, imap email...) could be registered with the same key in  CRUDityRegistry
    FetcherInterface abstract those to act like one fetcher
    """
    def __init__(self, fetchers):
        self.fetchers = fetchers
        self._inputs = defaultdict(dict)
        self._default_backend = None

    def add_fetcher(self, fetcher):
        self.fetchers.extend(fetcher)

    def add_inputs(self, *inputs):
        for input in inputs:
            self._inputs[input.name][input.method] = input

    def get_input(self, name, method):
        input_name = self._inputs.get(name)
        if input_name is not None:
            return input_name.get(method)

    def get_inputs(self):
        return self._inputs.values()

    def fetch(self):
        data = []
        for fetcher in self.fetchers:
            data.extend(fetcher.fetch())
        return data
#        return chain(fetcher.fetch() for fetcher in self.fetchers)

    def get_default_backend(self):
        """Special case, for retrieving the backend defined as the default one.
            The backend should be aware in his fetcher_fallback method that the input is not a dict of data but the raw data
            (i.e: An email object for the backend defined as the fallback of the email fetcher)
            To set a backend as the fallback the subject has to be fetcher_name/*
        """
        return self._default_backend

    def register_default_backend(self, backend):
        self._default_backend = backend


class CRUDityRegistry(object):
    def __init__(self):
        self._fetchers = {}
        self._backends   = {}

    def register_fetchers(self, source, fetchers):
        self._fetchers[source] = FetcherInterface(fetchers)

    def get_fetchers(self):
        return self._fetchers.values()

    def get_fetcher(self, source):
        return self._fetchers.get(source)

    def register_inputs(self, source, inputs):
        fetcher = self.get_fetcher(source)
        if fetcher is not None:
            fetcher.add_inputs(*inputs)
        else:
            warning(u"The fetcher '%s' does not exist, inputs : %s will not be registered" % (source, inputs))

    def register_backends(self, backends):
        for backend in backends:
            self._backends[backend.model] = backend

    def get_backends(self):
        """Get all registered backend
         @returns: A list of backend /!\classes (not instances)
        """
        return self._backends.values()

    def get_backend(self, model):
        """Get the registered backend class for the model"""
        try:
            return self._backends[model]
        except KeyError:
            raise NotRegistered("No backend is registered for this model '%s'" % model)

    def get_configured_backends(self):
        """Get backends instances which are configured and associated to an input (which is itself linked to a fetcher)
        @return: A list of configured backend instances
        """
        backends = []
        for fetcher in self.get_fetchers():
            for crud_inputs in fetcher.get_inputs():
                for input_type, input in crud_inputs.iteritems():
                    backends.extend(input.get_backends())
            default_be = fetcher.get_default_backend()
            if default_be is not None:
                backends.append(default_be)
        return backends

    def get_configured_backend(self, subject):
        for fetcher in self.get_fetchers():
            for crud_inputs in fetcher.get_inputs():
                for input_type, input in crud_inputs.iteritems():
                    backend = input.get_backend(CrudityBackend.normalize_subject(subject))
                    if backend is not None:
                        return backend

    def dispatch(self):
        for backend_cfg in settings.CRUDITY_BACKENDS:
            try:
                fetcher_source = backend_cfg.pop('fetcher')
                input_name     = backend_cfg.pop('input')
                model          = _get_model(backend_cfg.pop('model'))
                method         = backend_cfg.pop('method')
                backend        = self._backends.get(model)
                subject        = backend_cfg['subject']
                if backend is None:
                    raise NotRegistered("No backend is registered for this model '%s'" % model)
            except KeyError as e:
                raise ImproperlyConfigured(u"You have an error in your CRUDITY_BACKENDS settings. Check if '%s' is present" % e)
            except DeserializationError as de:
                raise ImproperlyConfigured(de)
            else:
                fetcher = self.get_fetcher(fetcher_source)
                input   = fetcher.get_input(input_name, method)
                if (fetcher and input) is not None:
                    backend_cfg['source'] = u"%s - %s" % (fetcher_source, input_name)
                    backend_cfg['verbose_source'] = input.verbose_name#for i18n
                    backend_cfg['verbose_method'] = input.verbose_method#for i18n
                    if subject == "*":
                        if fetcher.get_default_backend() is not None:
                            raise ImproperlyConfigured(u"Only one fallback backend is allowed for %s/%s" % (fetcher_source, input_name))
                        fetcher.register_default_backend(backend(backend_cfg))
                    else:
                        input.add_backend(backend(backend_cfg))

crudity_registry = CRUDityRegistry()

for crud_import in find_n_import("crudity_register", ['fetchers', 'inputs', 'models']):
    #Fetchers
    fetchers = getattr(crud_import, "fetchers", {})
    register_fetchers = crudity_registry.register_fetchers
    for source_type, fetchers_list in fetchers.iteritems():
        register_fetchers(source_type, fetchers_list)

    #Inputs
    inputs = getattr(crud_import, "inputs", {})
    register_inputs = crudity_registry.register_inputs
    for source_type, inputs_list in inputs.iteritems():
        register_inputs(source_type, inputs_list)

    #Backends (registered by models)
    backends = getattr(crud_import, "backends", [])
    crudity_registry.register_backends(backends)

crudity_registry.dispatch()
