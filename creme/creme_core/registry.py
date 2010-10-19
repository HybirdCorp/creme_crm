# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

class NotRegistered(Exception):
    pass


class CremeApp(object):
    __slots__ = ('name', 'verbose_name', 'url')

    def __init__(self, name, verbose_name, url):
        self.name = name
        self.verbose_name = verbose_name
        self.url = url


class CremeRegistry(object):
    """Registry for Creme Applications and Entities."""

    def __init__(self):
        self._entity_models = []
        self._apps = {}
        self._generic_registry = {}

    def register_app(self, name, verbose_name, url=None):
        self._apps[name] = CremeApp(name, verbose_name, url)

    def get_app(self, name):
        app = self._apps.get(name)

        if app is None:
            raise NotRegistered("%s.get_app(): No app registered with this name: %s" % (self.__class__, name))

        return app

    def iter_apps(self):
        return self._apps.itervalues()

    def register_entity_models(self, *models):
        """Register CremeEntity models."""
        self._entity_models.extend(models)

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
