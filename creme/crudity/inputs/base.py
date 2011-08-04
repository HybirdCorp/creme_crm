# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

class CrudityInput(object):
    name   = u""
    method = u""

    verbose_name   = u""
    verbose_method = u""

    def __init__(self):
        self.backends = {}
        self._buttons = []

    def add_backend(self, backend):
        backend.add_buttons(*self._buttons)
        self.backends[backend.subject] = backend

    def get_backends(self):
        return self.backends.values()

    def get_backend(self, subject):
        return self.backends.get(subject)

    def handle(self, data):
        """Call the method of the Input defined in subclasses
         @return: True if data were used else False
        """
        if hasattr(self, self.method):
            return getattr(self, self.method)(data)
        return False

    def register_buttons(self, *buttons):
        self._buttons.extend(buttons)

    def authorize_senders(self, backend, senders):
        return not backend.limit_froms or set(senders) & set(backend.limit_froms)

