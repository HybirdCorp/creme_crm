################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from collections.abc import Iterator

from django.contrib.contenttypes.models import ContentType
from django.db.models import Model
from django.forms import ModelForm

from creme.creme_core.gui.custom_form import CustomFormDescriptor
from creme.creme_core.models import CustomFormConfigItem
from creme.creme_core.utils.imports import import_apps_sub_modules


class RecurrentRegistry:
    """Register groups containing:
        - the model which will be recurrently instantiated (recurrent model).
        - the model use to instantiate the previous model (template model).
        - the model-form to create instances of template model (template form).
    """
    def __init__(self):
        self._template_forms = {}

    # TODO: do not pass <template_model>, use the template_form._meta.model ?
    # TODO: manage duplicates when registration is done from apps.py
    def register(self, *to_register):
        """
        @param to_register: tuples (recurrent model, template model, template form class) ;
               The form class can be a regular ModelForm class, or an instance of
               CustomFormDescriptor.
        """
        for model, template_model, template_form in to_register:
            self._template_forms[model] = template_form

    @property
    def models(self) -> Iterator[ContentType]:
        """Get the models which can be generated recurrently."""
        yield from self._template_forms.keys()

    def get_template_form_class(self, *, model: type[Model], user) -> type[ModelForm] | None:
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
