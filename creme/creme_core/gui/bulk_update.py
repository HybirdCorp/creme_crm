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

from creme.creme_core.models.custom_field import CustomField


class _BulkUpdateRegistry(object):
    class ModelBulkStatus(object):
        def __init__(self, model, ignore=False):
            self._model = model
            self.ignore = ignore

            self.excludes = set()
            self.innerforms = {}

        def is_updatable(self, field, exclude_unique=True):
            if isinstance(field, CustomField):
                return True

            return field.editable and not (exclude_unique and field.unique) and field.name not in self.excludes

        def updatables(self, exclude_unique=True):
            if self.ignore:
                return []

            is_updatable = self.is_updatable
            return (field for field in self._model._meta.fields if is_updatable(field, exclude_unique))

    def __init__(self):
        self._status = {}

    def _get_or_create_status(self, model):
        bulk = self._status.get(model)

        if bulk is None:
            bulk = self._status[model] = self.ModelBulkStatus(model)

        return bulk

    def register(self, model, exclude=None, innerforms=None):
        bulk = self._get_or_create_status(model)

        if exclude:
            bulk.excludes.update(set(exclude))

        bulk.innerforms.update(innerforms or {})

        # merge exclusion of subclasses
        for old_model, old_bulk in self._status.iteritems():
            if old_model is not model:
                # registered subclass inherits exclusions of new model 
                if issubclass(old_model, model):
                    old_bulk.exclude.update(bulk.exclude)

                # new model inherits exclusions of registered superclass
                if issubclass(model, old_model):
                    bulk.exclude.update(old_bulk.exclude)

        return bulk

    def ignore(self, model):
        bulk = self._get_or_create_status(model)
        bulk.ignore = True
        return bulk

    def status(self, model):
        bulk = self._status.get(model)

        # get excluded field by inheritance in case of working model is not registered yet
        if bulk is None:
            bulk = self.register(model)

        return bulk

    def is_updatable(self, model, field_name, exclude_unique=True):
        for field in self.status(model).updatables(exclude_unique):
            if field.name == field_name:
                return True

        return False


bulk_update_registry = _BulkUpdateRegistry()
