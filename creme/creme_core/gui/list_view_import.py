# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from django.contrib.contenttypes.models import ContentType


class FormRegistry(object):
    class UnregisteredCTypeException(Exception):
        pass

    def __init__(self):
        self._form_factories = {}

    def register(self, model, factory=None):
        """@param factory A callable that takes 2 parameters
        header_dict, a dictionary key=column slugified name; value=column index
        choices A list a choices, compliant with classical django Select widget.
         and which returns a form class that inherits creme_core.forms.list_view_import.ImportForm.
        'factory' can be None: it means that this ContentType use a generic import form.
        """
        self._form_factories[ContentType.objects.get_for_model(model).id] = factory

    def get(self, ct):
        try:
            return self._form_factories[ct.id]
        except KeyError:
            raise self.UnregisteredCTypeException('Unregistered ContentType: %s' % ct)

    def is_registered(self, ct):
        return ct.id in self._form_factories


import_form_registry = FormRegistry()
