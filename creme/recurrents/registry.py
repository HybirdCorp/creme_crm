# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

import warnings
from typing import Iterator, Optional, Type

from django.contrib.contenttypes.models import ContentType
from django.db.models import Model
from django.forms import ModelForm

from creme.creme_core.gui.custom_form import CustomFormDescriptor
from creme.creme_core.models import CustomFormConfigItem
from creme.creme_core.utils.imports import import_apps_sub_modules

# class TemplateRecurrentRegistry:
#     def __init__(self, model, template_model, template_form):
#         self.model = model
#         self.template_model = template_model
#         self.template_form = template_form
#
#
# class AppRecurrentRegistry:
#     def __init__(self, app_name):
#         self.app_name = app_name
#         self._templates = []
#
#     def add(self, model, template_model, template_form):
#         self._templates.append(
#             TemplateRecurrentRegistry(model, template_model, template_form)
#         )
#
#     def __iter__(self):
#         return iter(self._templates)


class RecurrentRegistry:
    """Register groups containing:
        - the model which will be recurrently instantiated (recurrent model).
        - the model use to instantiate the previous model (template model).
        - the model-form to create instances of template model (template form).
    """
    def __init__(self):
        # self._apps = {}
        self._template_forms = {}

    # TODO: do not pass <template_model>, use the template_form._meta.model ?
    # TODO: manage duplicates when registration is done from apps.py
    def register(self, *to_register):
        """
        @param to_register: tuples (recurrent model, template model, template form class) ;
               The form class can be a regular ModelForm class, or an instance of
               CustomFormDescriptor.
        """
        # app_registries = self._apps
        #
        # for model, template_model, template_form in to_register:
        #     app_name = model._meta.app_label
        #     app_registry = app_registries.get(app_name)
        #
        #     if app_registry is None:
        #         app_registry = app_registries[app_name] = AppRecurrentRegistry(app_name)
        #
        #     app_registry.add(model, template_model, template_form)
        for model, template_model, template_form in to_register:
            self._template_forms[model] = template_form

    @property
    def ctypes(self) -> Iterator[ContentType]:
        """Generates the ContentTypes of recurrent models."""
        warnings.warn(
            'The property RecurrentRegistry.ctypes is deprecated ; '
            'use "models" instead.',
            DeprecationWarning,
        )

        get_ct = ContentType.objects.get_for_model

        # for app_registry in self._apps.values():
        #     for template_entry in app_registry:
        #         yield get_ct(template_entry.model)
        for model in self.models:
            yield get_ct(model)

    @property
    def models(self) -> Iterator[ContentType]:
        """Get the models which can be generated recurrently."""
        yield from self._template_forms.keys()

    # def get_form_of_template(self, ct_template: ContentType) -> Optional[Type[ModelForm]]:
    #     "Get the form class from the ContentType of a template model."
    #     model = ct_template.model_class()
    #
    #     for app_registry in self._apps.values():
    #         for template_entry in app_registry:
    #             if template_entry.model == model:
    #                 form_class = template_entry.template_form
    #
    #                 return (
    #                     form_class.build_form_class()
    #                     if isinstance(form_class, CustomFormDescriptor) else
    #                     form_class
    #                 )

    def get_template_form_class(self, *, model: Type[Model], user) -> Optional[Type[ModelForm]]:
        """Get the form class (for a template model) related to a given model."""
        form_class = self._template_forms.get(model)
        if form_class:
            return (
                form_class.build_form_class(
                    item=CustomFormConfigItem.objects.get_for_user(
                        descriptor=form_class, user=user,
                    ),
                )
                if isinstance(form_class, CustomFormDescriptor) else
                form_class
            )

        return None


recurrent_registry = RecurrentRegistry()

for recurrents_import in import_apps_sub_modules('recurrents_register'):
    recurrent_registry.register(*recurrents_import.to_register)
