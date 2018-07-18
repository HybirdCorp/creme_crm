# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

# import logging


# logger = logging.getLogger(__name__)


class QuickFormsRegistry:
    class RegistrationError(Exception):
        pass

    def __init__(self):
        self._forms = {}

    def register(self, model, form):
        forms = self._forms

        if model in forms:
            # logger.warning("A Quick Form is already registered for the model : %s", model)
            raise self.RegistrationError('A Quick Form is already registered for the model : {}'.format(model))

        forms[model] = form

    def unregister(self, model):
        try:
            self._forms.pop(model)
        except KeyError as e:
            raise self.RegistrationError('No Quick Form is registered for the model : {}'.format(model)) from e

    def iter_models(self):
        return self._forms.keys()

    def get_form(self, model):
        return self._forms.get(model)


quickforms_registry = QuickFormsRegistry()
