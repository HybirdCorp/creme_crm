# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

from ..backends.gui import TemplateBrickHeaderAction


class CrudityInput:
    name   = ''
    method = ''

    verbose_name   = ''
    verbose_method = ''

    brickheader_action_templates = ()

    def __init__(self):
        self._backends = {}
        self._brickheader_actions = [
            TemplateBrickHeaderAction(template_name=tn)
                for tn in self.brickheader_action_templates
        ]

    def add_backend(self, backend):
        self._backends[backend.subject] = backend

    def get_backends(self):  # TODO: rename 'backends' + property + generator ?
        return [*self._backends.values()]

    def get_backend(self, subject):
        return self._backends.get(subject)

    @property
    def has_backends(self):
        return bool(self._backends)

    def handle(self, data):
        """Call the method of the Input defined in subclasses.
        @return: The backend used if data were used else None.
        """
        fun = getattr(self, self.method, None)
        if fun:
            return fun(data)

        return None

    @property
    def brickheader_actions(self):
        return iter(self._brickheader_actions)

    def authorize_senders(self, backend, senders):
        return not backend.limit_froms or {*senders} & {*backend.limit_froms}
