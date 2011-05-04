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
from logging import warning

class BulkUpdateRegistry(object):
    def __init__(self):
        self._excluded_fields_names = {}

    def register(self, *fields_to_exclude):
        _excluded_fields_names = self._excluded_fields_names

        for model, fields in fields_to_exclude:
            if _excluded_fields_names.has_key(model):
                warning("Fields of model <%s> registered twice", model) #exception instead ???

            _excluded_fields_names[model] = fields

    def get_excluded_fields(self, model):
        return self._excluded_fields_names.get(model, [])

    
bulk_update_registry = BulkUpdateRegistry()
