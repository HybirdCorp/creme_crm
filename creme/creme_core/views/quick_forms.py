# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

from django.http import Http404
from django.utils.functional import cached_property

from ..gui.quick_forms import quickforms_registry
from . import generic
from .generic.base import EntityCTypeRelatedMixin
from .utils import json_update_from_widget_response


# TODO: manage/display error (like PermissionDenied) on JS side (for now it just does nothing)
class QuickCreation(EntityCTypeRelatedMixin, generic.EntityCreationPopup):
    # model = ...
    # form_class = ...
    template_name = 'creme_core/generics/form/add-popup.html'

    quickforms_registry = quickforms_registry

    def get_form_class(self):
        model = self.model
        form_class = self.quickforms_registry.get_form_class(model)

        if form_class is None:
            raise Http404(f'No form registered for model: {model}')

        return form_class

    def form_valid(self, form):
        super().form_valid(form=form)
        return json_update_from_widget_response(form.instance)

    @cached_property
    def model(self):
        return self.get_ctype().model_class()
