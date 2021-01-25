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

# import warnings
from typing import TYPE_CHECKING, Dict, Iterator, Optional, Type

from creme.creme_core.models import CremeEntity

if TYPE_CHECKING:
    from creme.creme_core.forms.base import CremeEntityQuickForm


class QuickFormsRegistry:
    """Registry for "quick" forms, ie small forms which can be easily used in an
    inner-popup to create entities on-the-go.

    These forms are used :
      - in the main menu (entry "+Creation").
      - in the form-fields to link to other entities (eg: CreatorEntityField).

    Each form-class is associated to a model (class inheriting CremeEntity).
    """
    class RegistrationError(Exception):
        pass

    def __init__(self):
        self._forms: Dict[Type[CremeEntity], Type['CremeEntityQuickForm']] = {}

    # TODO: rename form=>form_class
    def register(self,
                 model: Type[CremeEntity],
                 form: Type['CremeEntityQuickForm']) -> 'QuickFormsRegistry':
        """Register a form for a given model.
        @raise RegistrationError if a form is already registered.
        """
        from creme.creme_core.forms.base import CremeEntityQuickForm

        forms = self._forms

        if model in forms:
            raise self.RegistrationError(
                f'A Quick Form is already registered for the model : {model}'
            )

        if not issubclass(form, CremeEntityQuickForm):
            raise self.RegistrationError(
                f'A Quick Form class must inherit '
                f'<creme_core.forms.base.CremeEntityQuickForm> : {form}'
            )

        forms[model] = form

        return self

    def unregister(self, model: Type[CremeEntity]) -> None:
        """Un-register the form related to a given model.
        @raise RegistrationError if no form is registered.
        """
        try:
            self._forms.pop(model)
        except KeyError as e:
            raise self.RegistrationError(
                f'No Quick Form is registered for the model : {model}'
            ) from e

    # def iter_models(self):
    #     warnings.warn('QuickFormsRegistry.iter_models() is deprecated ;'
    #                   'use @models instead.',
    #                   DeprecationWarning
    #                  )
    #     return self._forms.keys()

    # def get_form(
    #         self,
    #         model: Type[CremeEntity]) -> Optional[Type['CremeEntityQuickForm']]:
    #     warnings.warn('QuickFormsRegistry.get_form() is deprecated ;'
    #                   'use get_form_class() instead.',
    #                   DeprecationWarning
    #                  )
    #     return self._forms.get(model)

    def get_form_class(
            self,
            model: Type[CremeEntity]) -> Optional[Type['CremeEntityQuickForm']]:
        return self._forms.get(model)

    @property
    def models(self) -> Iterator[Type[CremeEntity]]:
        "All the models which get a quick-form."
        return iter(self._forms.keys())


quickforms_registry = QuickFormsRegistry()
