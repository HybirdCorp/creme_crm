# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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

from django.utils.datastructures import OrderedSet

logger = logging.getLogger(__name__)


class NotRegistered(Exception):
    pass


class CremeApp(object):
    __slots__ = ('name', 'verbose_name', 'url', 'credentials', 'extended_app')

    def __init__(self, name, verbose_name, url, credentials, extended_app=None):
        self.name = name
        self.verbose_name = verbose_name
        self.url = url
        self.credentials = credentials
        self.extended_app = extended_app


class CremeRegistry(object):
    """Registry for Creme Applications and Entities."""
    CRED_NONE    = 0b00
    CRED_REGULAR = 0b01
    CRED_ADMIN   = 0b10

    def __init__(self):
        self._entity_models = OrderedSet()
        self._apps = {}
        self._extending_apps = defaultdict(list)
        self._generic_registry = {}

    def register_app(self, name, verbose_name, url=None,
                     credentials=CRED_REGULAR|CRED_ADMIN,
                     extended_app=None,
                    ):
        if extended_app is not None:
            # TODO: check that's a valid app name
            credentials = self.CRED_NONE
            self._extending_apps[extended_app].append(name)

        self._apps[name] = CremeApp(name, verbose_name, url, credentials, extended_app)

    def get_app(self, name, silent_fail=False):
        app = self._apps.get(name)

        if app is None:
            error_msg = "%s.get_app(): No app registered with this name: %s" % (self.__class__, name)
            if silent_fail:
                logger.critical(error_msg)
            else:
                raise NotRegistered(error_msg)

        return app

    def get_extending_apps(self, name):
        return iter(self._extending_apps[name])

    def iter_apps(self):
        return self._apps.itervalues()

    def register_entity_models(self, *models):
        """Register CremeEntity models."""
        from .models import CremeEntity

        entity_models = self._entity_models

        for model in models:
            if not issubclass(model, CremeEntity):
                logger.critical('CremeRegistry.register_entity_models: "%s" is not'
                                ' a subclass of CremeEntity, so we ignore it', model,
                               )
                continue

            # ordering = model._meta.ordering
            # if not ordering or ordering[0] == 'id':
            #     logger.warn('CremeRegistry.register_entity_models: "%s" should'
            #                 ' have a Meta.ordering different from "id", so we'
            #                 ' give it a default one', model,
            #                )
            #     model._meta.ordering = ('header_filter_search_field',)

            entity_models.add(model)

    def is_entity_model_registered(self, model):
        return model in self._entity_models

    def iter_entity_models(self):
        return iter(self._entity_models)

    def register(self, key, value):
        """A generic registry map"""
        self._generic_registry[key] = value

    def get(self, key):
        value = self._generic_registry.get(key)

        if value is None:
            raise NotRegistered("Nothing registered with this key: %s" % (key,))

        return value

creme_registry = CremeRegistry()
