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

class BulkUpdateRegistry(object):
    def __init__(self):
        self._excluded_fields_names = {}
        self._excluded_fields_names_cache = None

    def _build_cache(self):
        self._excluded_fields_names_cache = {}
        _excluded_fields_names_cache = self._excluded_fields_names_cache
        _excluded_fields_names_get = self._excluded_fields_names.get

        for model, fields in self._excluded_fields_names.iteritems():
            for model_key in self._excluded_fields_names.iterkeys():
                if issubclass(model, model_key) and not model_key is model:
                    fields |= _excluded_fields_names_get(model_key)

            _excluded_fields_names_cache[model] = fields

    def _register(self, *fields_to_exclude):
        _excluded_fields_names = self._excluded_fields_names
        
        for model, fields in fields_to_exclude:
            if _excluded_fields_names.has_key(model):
                #warning("Fields of model <%s> registered twice", model)
                _excluded_fields_names[model] |= set(fields)#If another app have to overide an already registered model
            else:
                _excluded_fields_names[model] = set(fields)

    def register(self, *fields_to_exclude):
        self._register(*fields_to_exclude)
        self._build_cache()

    def get_excluded_fields(self, model):
        """
        @params model: A django model
        Returns a set of excluded fields names for this model
        """
        if self._excluded_fields_names_cache is None:
            self._build_cache()

        excluded_fields = self._excluded_fields_names_cache.get(model)

        print "excluded_fields1 ", excluded_fields

        if excluded_fields is None:#This model is not registered but its parent class may be
            _cache_get = self._excluded_fields_names_cache.get
            _found = False
            excluded_fields = set()

            for model_key in self._excluded_fields_names_cache.iterkeys():
                if issubclass(model, model_key):
                    self._register((model, _cache_get(model_key)))#We register it as it was registered
                    _found = True

            if _found:
                self._build_cache()
                excluded_fields = self._excluded_fields_names_cache.get(model)

        return excluded_fields


bulk_update_registry = BulkUpdateRegistry()
