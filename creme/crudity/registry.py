# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2017  Hybird
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
from copy import deepcopy
import logging, warnings

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.serializers.base import DeserializationError
from django.core.serializers.python import _get_model

from creme.creme_core.registry import NotRegistered
from creme.creme_core.utils.collections import OrderedSet
from creme.creme_core.utils.imports import find_n_import

# from creme.crudity.backends.models import CrudityBackend


logger = logging.getLogger(__name__)
ALLOWED_ID_CHARS = OrderedSet('abcdefghijklmnopqrstuvwxyz'
                              'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.'
                             )


class FetcherInterface(object):
    """Multiple fetchers of the same "type" (i.e: pop email, imap email...) could
    be registered with the same key in CRUDityRegistry.
    FetcherInterface abstract those to act like one fetcher.
    """
    def __init__(self, fetchers):
        # self.fetchers = fetchers
        self.fetchers = list(fetchers)
        self._inputs = defaultdict(dict)
        self._default_backend = None

    def add_fetcher(self, fetcher):
        warnings.warn('FetcherInterface.add_fetcher() is deprecated ; use add_fetchers() instead.',
                      DeprecationWarning,
                     )
        self.fetchers.extend(fetcher)

    def add_fetchers(self, fetchers):
        self.fetchers.extend(fetchers)

    def add_inputs(self, *inputs):
        for crud_input in inputs:
            self._inputs[crud_input.name][crud_input.method] = crud_input

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
        self._backends = {}

    def __unicode__(self):
        res = 'CRUDityRegistry:'

        for fetcher_name, fetcher_interface in self._fetchers.iteritems():
            res += '\n - Fetcher("%s"): %s' % (fetcher_name, '/'.join(unicode(fetcher.__class__.__name__) for fetcher in fetcher_interface.fetchers))

            default_backend = fetcher_interface.get_default_backend()
            if default_backend:
                res += '    Default backend: %s' % default_backend

            for input_name, inputs in fetcher_interface._inputs.iteritems():
                res += '\n    - Input("%s"):' % input_name

                for method, input in inputs.iteritems():
                    res += '\n       - Method "%s": <%s>' % (method, input.__class__.__name__)

                    backends = input.backends

                    if not backends:
                        res += ' -> No BACKEND'
                    else:
                        res += '\n         Backends:'
                        for subject, backend in input.backends.iteritems():
                            res += '\n          - %s: %s' % (subject, backend.__class__.__name__)

        return res

    def autodiscover(self):
        for crud_import in find_n_import('crudity_register', ['fetchers', 'inputs', 'backends']):
            # Fetchers
            fetchers = getattr(crud_import, 'fetchers', {})
            register_fetchers = self.register_fetchers
            # for source_type, fetchers_list in fetchers.iteritems():
            for source_type, fetchers_classes in fetchers.iteritems():
                if any(c not in ALLOWED_ID_CHARS for c in source_type):
                    raise ValueError('The fetchers ID "%s" (in %s) use forbidden characters [allowed ones: %s].' % (
                                            source_type, crud_import, ''.join(ALLOWED_ID_CHARS),
                                        )
                                    )

                # register_fetchers(source_type, fetchers_list)
                register_fetchers(source_type, [fetcher_cls() for fetcher_cls in fetchers_classes])

            # Inputs
            inputs = getattr(crud_import, 'inputs', {})
            register_inputs = self.register_inputs
            # for source_type, inputs_list in inputs.iteritems():
            for source_type, input_classes in inputs.iteritems():
                for crud_input in input_classes:
                    if any(c not in ALLOWED_ID_CHARS for c in crud_input.name):
                        raise ValueError('The input ID "%s" (%s) use forbidden characters [allowed ones: %s].' % (
                                                crud_input.name, crud_input.__class__, ''.join(ALLOWED_ID_CHARS),
                                            )
                                        )

                # register_inputs(source_type, inputs_list)
                register_inputs(source_type, [input_cls() for input_cls in input_classes])

            # Backends (registered by models)
            backends = getattr(crud_import, 'backends', [])
            self.register_backends(backends)

    def register_fetchers(self, source, fetchers):
        # self._fetchers[source] = FetcherInterface(fetchers)
        fetcher_multiplex = self._fetchers.get(source)

        # TODO: defaultdict...
        if fetcher_multiplex is None:
            self._fetchers[source] = FetcherInterface(fetchers)
        else:
            fetcher_multiplex.add_fetchers(fetchers)

    def get_fetchers(self):
        return self._fetchers.values()

    def get_fetcher(self, source):
        return self._fetchers.get(source)

    def register_inputs(self, source, inputs):
        fetcher = self.get_fetcher(source)

        if fetcher is not None:
            fetcher.add_inputs(*inputs)
        else:
            logger.warning(u"The fetcher '%s' does not exist, inputs '%s' will not be registered",
                           source, inputs,
                          )

    def register_backends(self, backends):
        for backend in backends:
            # TODO: error if model is already associated with the model ? (or a log in order to override cleanly)
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
            raise NotRegistered("No backend is registered for the model '%s'" % model)

    def get_configured_backends(self):
        """Get backends instances which are configured and associated to an input
        (which is itself linked to a fetcher).
        @return: A list of configured backend instances
        """
        backends = []

        for fetcher in self.get_fetchers():
            for crud_inputs in fetcher.get_inputs():
                # for input_type, input in crud_inputs.iteritems():
                for crud_input in crud_inputs.itervalues():
                    # backends.extend(input.get_backends())
                    backends.extend(crud_input.get_backends())

            default_be = fetcher.get_default_backend()

            if default_be is not None:
                backends.append(default_be)

        return backends

    # def get_configured_backend(self, subject):
    #     for fetcher in self.get_fetchers():
    #         for crud_inputs in fetcher.get_inputs():
    #             for input_type, input in crud_inputs.iteritems():
    #                 backend = input.get_backend(CrudityBackend.normalize_subject(subject))
    #
    #                 if backend is not None:
    #                     return backend
    def get_configured_backend(self, fetcher_name, input_name, norm_subject):
        try:
            fetcher = self._fetchers[fetcher_name]
        except KeyError:
            raise KeyError('Fetcher not found: ' + fetcher_name)

        try:
            crud_inputs = fetcher._inputs[input_name] # TODO: FetcherInterface method ?
        except KeyError:
            raise KeyError('Input not found: ' + input_name)

        for crud_input in crud_inputs.itervalues():
            backend = crud_input.get_backend(norm_subject)

            if backend:
                return backend

        raise KeyError('Backend not found: ' + norm_subject)

    def get_default_backend(self, fetcher_name):
        fetcher = crudity_registry.get_fetcher(fetcher_name)
        if not fetcher:
            raise KeyError('Unknown fetcher "%s"' % fetcher_name)

        backend = fetcher.get_default_backend()
        if not backend:
            raise KeyError('Fetcher "%s" has no default backend' % fetcher_name)

        return backend

    # def dispatch(self):
    #     for backend_cfg in settings.CRUDITY_BACKENDS:
    #         backend_cfg = deepcopy(backend_cfg)
    #
    #         try:
    #             fetcher_source = backend_cfg.pop('fetcher')
    #             input_name     = backend_cfg.pop('input')
    #             model          = _get_model(backend_cfg.pop('model'))
    #             method         = backend_cfg.pop('method')
    #             backend        = self._backends.get(model)
    #             subject        = backend_cfg['subject']
    #             if backend is None:
    #                 raise NotRegistered("No backend is registered for this model '%s'" % model)
    #         except KeyError as e:
    #             raise ImproperlyConfigured(u"You have an error in your CRUDITY_BACKENDS settings. Check if '%s' is present" % e)
    #         except DeserializationError as de:
    #             raise ImproperlyConfigured(de)
    #         else:
    #             fetcher = self.get_fetcher(fetcher_source)
    #             crud_input = fetcher.get_input(input_name, method)
    #
    #             if (fetcher and crud_input) is not None:
    #                 backend_cfg['source'] = u"%s - %s" % (fetcher_source, input_name)
    #                 backend_cfg['verbose_source'] = crud_input.verbose_name #for i18n
    #                 backend_cfg['verbose_method'] = crud_input.verbose_method #for i18n
    #
    #                 if subject == "*":
    #                     if fetcher.get_default_backend() is not None:
    #                         raise ImproperlyConfigured(u"Only one fallback backend is allowed for %s/%s" % (
    #                                                         fetcher_source, input_name,
    #                                                     )
    #                                                   )
    #
    #                     fetcher.register_default_backend(backend(backend_cfg))
    #                 else:
    #                     crud_input.add_backend(backend(backend_cfg))
    def dispatch(self, backend_configs):
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
                raise ImproperlyConfigured(u'You have an error in your CRUDITY_BACKENDS settings. '
                                           u'Check if "%s" is present' % e
                                          )
            except DeserializationError as de:
                raise ImproperlyConfigured(de)
            else:
                backend_cls = self._backends.get(model)
                if backend_cls is None:
                    raise ImproperlyConfigured(u'settings.CRUDITY_BACKENDS: '
                                               u'no backend is registered for this model <%s>' % model
                                              )

                fetcher = self.get_fetcher(fetcher_source)

                if fetcher is None:
                    raise ImproperlyConfigured(u'settings.CRUDITY_BACKENDS: '
                                               u'invalid fetcher "%s".' % fetcher_source
                                              )

                if subject == '*':
                    if fetcher.get_default_backend() is not None:
                        raise ImproperlyConfigured(u'settings.CRUDITY_BACKENDS: '
                                                   u'only one fallback backend is allowed for "%s/%s".' % (
                                                       fetcher_source, input_name,
                                                    )
                                                  )

                    backend_cfg['source'] = fetcher_source
                    backend_instance = backend_cls(backend_cfg)

                    if not hasattr(backend_instance, 'fetcher_fallback'):
                        raise ImproperlyConfigured(u'settings.CRUDITY_BACKENDS: '
                                                   u'the backend for %s cannot be used as fallback '
                                                   u'(ie: subject="*").' % model
                                                  )

                    backend_instance.fetcher_name = fetcher_source

                    fetcher.register_default_backend(backend_instance)
                else:
                    if not input_name:
                        raise ImproperlyConfigured(u'settings.CRUDITY_BACKENDS: '
                                                   u'you have to declare an input for the fetcher %s.' % fetcher_source
                                                  )

                    if not method:
                        raise ImproperlyConfigured(u'settings.CRUDITY_BACKENDS: '
                                                   u'you have to declare a method for "%s/%s".' % (
                                                        fetcher_source, input_name
                                                    )
                                                  )

                    crud_input = fetcher.get_input(input_name, method)

                    if not crud_input:
                        raise ImproperlyConfigured(u'settings.CRUDITY_BACKENDS: '
                                                   u'invalid input "%s" for the fetcher "%s".' % (
                                                        input_name, fetcher_source
                                                   )
                                                  )

                    # TODO: move this code to backend
                    backend_cfg['source'] = u'%s - %s' % (fetcher_source, input_name)
                    backend_cfg['verbose_source'] = crud_input.verbose_name  # For i18n
                    backend_cfg['verbose_method'] = crud_input.verbose_method  # For i18n

                    backend_instance = backend_cls(backend_cfg, crud_input=crud_input)
                    backend_instance.fetcher_name = fetcher_source
                    backend_instance.input_name = input_name

                    if crud_input.get_backend(backend_instance.subject):
                        raise ImproperlyConfigured(u'settings.CRUDITY_BACKENDS: '
                                                   u'this (normalised) subject must be unique for "%s/%s": %s' % (
                                                        fetcher_source, input_name, backend_instance.subject
                                                    )
                                                  )

                    crud_input.add_backend(backend_instance)

    def fetch(self, user):
        used_backends = []

        def _handle_data(multi_fetcher, data):
            for inputs_per_method in multi_fetcher.get_inputs():
                for crud_input in inputs_per_method.itervalues():
                    handling_backend = crud_input.handle(data)

                    if handling_backend is not None:
                        return handling_backend

                default_backend = multi_fetcher.get_default_backend()

                if default_backend is not None:
                    default_backend.fetcher_fallback(data, user)
                    return default_backend

        for fetcher_multiplex in self.get_fetchers():
            # TODO: FetcherInterface.has_backends() ?
            if not any(crud_input.backends
                           for inputs_per_method in fetcher_multiplex.get_inputs()
                               for crud_input in inputs_per_method.itervalues()
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
