# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from itertools import chain
from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.db.models.fields import FieldDoesNotExist
from django.db.models.fields.related import ForeignKey
from django.utils.translation import ugettext

from creme.creme_core.models.custom_field import CustomField
from creme.creme_core.utils.unicode_collation import collator

class FieldNotAllowed(Exception):
    pass

class _BulkUpdateRegistry(object):
    class ModelBulkStatus(object):
        def __init__(self, model, ignore=False):
            self._model = model
            self.ignore = ignore

            self.excludes = set()
            self.fields = set()

            self._innerforms = {}
            self._regularfields = {}
            self._customfields = {}

        def is_expandable(self, field):
            return isinstance(field, ForeignKey) and not field.get_tag('enumerable')

        def is_allowed(self, field):
            fieldname = field.name

            if isinstance(field, CustomField) or field.editable:
                return fieldname not in self.excludes

            return fieldname in self.fields

        @property
        def regular_fields(self):
            if self.ignore:
                return {}

            if self._regularfields:
                return self._regularfields

            regular_fields = chain(self._model._meta.fields, self._model._meta.many_to_many)
            self._regularfields = {field.name: field for field in regular_fields}

            return self._regularfields

        @property
        def allowed_regular_fields(self):
            is_allowed = self.is_allowed
            return {key: field for key, field in self.regular_fields.iteritems() if is_allowed(field)}

        @property
        def custom_fields(self):
            if self.ignore:
                return {}

            model = self._model

            custom_fields = {'customfield-%d' % field.pk: field for field in
                                CustomField.objects.filter(content_type=ContentType.objects.get_for_model(model))
                            }

            for field in custom_fields.values():
                field.model = self._model

            return custom_fields

        def get_field(self, name):
            if name.startswith('customfield-'):
                field = self.custom_fields.get(name)
            else:
                field = self.regular_fields.get(name)

                if field and not self.is_allowed(field):
                    raise FieldNotAllowed(u"The field %s.%s is not editable" % (self._model._meta.verbose_name, name))

            if field is None:
                raise FieldDoesNotExist(u"The field %s.%s doesn't exist" % (self._model._meta.verbose_name, name))

            return field

        def get_form(self, name, default=None):
            return self._innerforms.get(name, default)

    def __init__(self):
        self._status = {}

    def _get_or_create_status(self, model):
        bulk = self._status.get(model)

        if bulk is None:
            bulk = self._status[model] = self.ModelBulkStatus(model)

        return bulk

    def register(self, model, exclude=None, fields=None, innerforms=None):
        bulk = self._get_or_create_status(model)

        if exclude:
            bulk.excludes.update(set(exclude))

        if fields:
            bulk.fields.update(set(fields))

        if innerforms:
            bulk._innerforms.update(dict(innerforms))

        # merge exclusion of subclasses
        for old_model, old_bulk in self._status.iteritems():
            if old_model is not model:
                # registered subclass inherits exclusions of new model 
                if issubclass(old_model, model):
                    old_bulk.excludes.update(bulk.excludes)
                    old_bulk.fields.update(bulk.fields)

                # new model inherits exclusions and custom forms of registered superclass
                if issubclass(model, old_model):
                    bulk.excludes.update(old_bulk.excludes)
                    bulk.fields.update(old_bulk.fields)

                    merged_innerforms = dict(old_bulk._innerforms)
                    merged_innerforms.update(bulk._innerforms)
                    bulk._innerforms = merged_innerforms

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

    def get_default_field(self, model):
        status = self.status(model)
        return sorted(status.regular_fields.values(), key=lambda f: ugettext(f.verbose_name))[0]

    def get_field(self, model, field_name):
        status = self.status(model)
        field_basename, _sep_, subfield_name = field_name.partition('__')

        field = status.get_field(field_basename)

        if field and subfield_name and status.is_expandable(field):
            field = self.get_field(field.rel.to, subfield_name)

        return field

    def get_form(self, model, field_name, default=None):
        status = self.status(model)
        field_basename, _sep_, subfield_name = field_name.partition('__')

        field = status.get_field(field_basename)

        if subfield_name and status.is_expandable(field):
            substatus = self.status(field.rel.to)
            subfield = substatus.get_field(subfield_name)
            form = substatus.get_form(subfield_name, default)

            return partial(form,
                           field=subfield,
                           parent_field=field) if form else None

        form = status.get_form(field_basename, default)
        return partial(form, field=field) if form else None

    def is_updatable(self, model, field_name, exclude_unique=True):
        try:
            field = self.get_field(model, field_name)
        except (FieldDoesNotExist, FieldNotAllowed):
            return False

        return not (exclude_unique and field.unique)

    def regular_fields(self, model, expand=False, exclude_unique=True):
        sort_key = collator.sort_key

        status = self.status(model)
        fields = status.allowed_regular_fields.values()

        if exclude_unique:
            fields = [field for field in fields if not field.unique]

        if expand is True:
            related_fields = self.regular_fields
            is_expandable = status.is_expandable

            fields = [(field, related_fields(model=field.rel.to, exclude_unique=exclude_unique) if is_expandable(field) else None)
                      for field in fields]

            return sorted(fields, key=lambda f: sort_key(f[0].name))

        return sorted(fields, key=lambda f: sort_key(f.name))

    def custom_fields(self, model):
        sort_key = collator.sort_key
        return sorted(self.status(model).custom_fields.values(), key=lambda f: sort_key(f.name))


bulk_update_registry = _BulkUpdateRegistry()

