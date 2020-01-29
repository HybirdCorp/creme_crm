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

from typing import Type, Dict, Optional

from django.forms.forms import BaseForm

from creme.creme_core.models import CremeEntity


class QuickFormsRegistry:
    class RegistrationError(Exception):
        pass

    def __init__(self):
        self._forms: Dict[Type[CremeEntity], Type[BaseForm]] = {}

    # TODO: rename form=>form_class
    def register(self, model: Type[CremeEntity], form: Type[BaseForm]) -> None:
        forms = self._forms

        if model in forms:
            raise self.RegistrationError(
                f'A Quick Form is already registered for the model : {model}'
            )

        forms[model] = form

    def unregister(self, model: Type[CremeEntity]) -> None:
        try:
            self._forms.pop(model)
        except KeyError as e:
            raise self.RegistrationError(
                f'No Quick Form is registered for the model : {model}'
            ) from e

    # TODO: @property "models" + Iterator
    def iter_models(self):
        return self._forms.keys()

    # TODO: rename get_form_class
    def get_form(self, model: Type[CremeEntity]) -> Optional[Type[BaseForm]]:
        return self._forms.get(model)


quickforms_registry = QuickFormsRegistry()
