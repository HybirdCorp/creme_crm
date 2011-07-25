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

from itertools import chain
from logging import warning

from creme_core.utils.imports import find_n_import

from crudity import CREATE, READ, UPDATE, DELETE
from crudity.backends.email import CreateFromEmailBackend

class NotValidFromEmailCRUDBackend(Exception):
    pass

#TODO: FromEmailBackends have (crud) type so register by [type][name] and derivate from a FromEmailBackend class ?
#To TODO: For now, only create backends are created and they have to derivate from CreateFromEmailBackend
class FromEmailCRUDRegistry(object):
#    __slots__ = ('_registry', '_registers)

    def __init__(self):
        self._registers = {
            CREATE: self.register_creates,
        }

        self._registry = {
            CREATE: {},
            READ  : {},
            UPDATE: {},
            DELETE: {}

        }

    def register(self, key, to_register):
        crud_registry = self._registers.get(key)

        if crud_registry is not None:
            crud_registry(*to_register)

    def register_creates(self, *backends):
        creates = self._registry[CREATE]

        for name, backend in backends:
            assert issubclass(backend.__class__, CreateFromEmailBackend)
            name = name.upper()
            if creates.has_key(name):
                if name == "*":
                    raise NotValidFromEmailCRUDBackend("Only one fallback backend allowed")
                else:
                    warning("Duplicate create CRUD backend or backend registered twice : %s", name) #exception instead ???

            creates[name] = backend


    def get_create(self, name):
        return self._registry[CREATE].get(name)


    def get(self, type, key):
        return {
            CREATE: self.get_create

        }.get(type, lambda x:None)(key)

    def iteritems(self):
        return chain(self._registry[CREATE].iteritems(),
                     self._registry[READ].iteritems(),
                     self._registry[UPDATE].iteritems(),
                     self._registry[DELETE].iteritems(),)

    def iter_creates_values(self):
        return self._registry[CREATE].itervalues()

    def get_creates(self):
        return self._registry[CREATE]


from_email_crud_registry = FromEmailCRUDRegistry()

email_crud_imports = find_n_import("crudity_email_register", ['crud_register'])

for email_crud_import in email_crud_imports:
    for crud_name, to_register in email_crud_import.crud_register.items():
        from_email_crud_registry.register(crud_name, to_register)
