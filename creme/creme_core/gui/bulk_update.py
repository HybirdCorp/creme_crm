# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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


class _BulkUpdateRegistry(object):
    def __init__(self):
        self._excluded_fieldnames = {} #key: model / values: set of field names (strings)

    def register(self, *fields_to_exclude):
        excluded_fieldnames = self._excluded_fieldnames

        for new_model, new_names in fields_to_exclude:
            new_names = set(new_names)

            for model, names in excluded_fieldnames.iteritems():
                if new_model is not model:
                    if issubclass(model, new_model):
                        names |= new_names
                    elif issubclass(new_model, model):
                        new_names |= names

            old_names = excluded_fieldnames.get(new_model)

            if old_names is None:
                excluded_fieldnames[new_model] = new_names
            else:
                old_names |= new_names

    def get_fields(self, model, exclude_unique=True):
        excluded_fields = self._excluded_fieldnames.get(model)

        # get excluded field by inheritance in case of working model is not registered yet
        if excluded_fields is None:
            self.register((model, []))
            excluded_fields = self._excluded_fieldnames.get(model)

        for field in model._meta.fields:
            if field.editable and field.name not in excluded_fields and not (exclude_unique and field.unique):
                yield field

    def is_bulk_updatable(self, model, field_name, exclude_unique=True):
        for field in self.get_fields(model, exclude_unique=exclude_unique):
            if field.name == field_name:
                return True


bulk_update_registry = _BulkUpdateRegistry()
