# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from logging import warning


class QuickFormsRegistry(object):
    def __init__(self):
        self._forms = {}

    def register(self, model, form):
        forms = self._forms

        if forms.has_key(model):
            warning("A Quick Form is alerady registered for the model : %s", model) #exception instead ???

        forms[model] = form

    def iter_models(self):
        return self._forms.iterkeys()

    def get_form(self, model):
        return self._forms[model]


quickforms_registry = QuickFormsRegistry()
