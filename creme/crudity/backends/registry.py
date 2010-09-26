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

from crudity import CREATE
from crudity.backends.email import CreateFromEmailBackend

class NotValidFromEmailCRUDBackend(Exception):
    pass

#TODO: FromEmailBackends have (crud) type so register by [type][name] and derivate from a FromEmailBackend class ?
class FromEmailCRUDRegistry(object):
#    __slots__ = ('_creates', '_reads', '_updates', '_delete')

    def __init__(self):
        self._creates = {}
        self._reads   = {}
        self._updates = {}
        self._delete  = {}

    def register(self, key, to_register):
        {
            CREATE: self.register_creates,
            
        }[key](*to_register)

    def register_creates(self, *backends):
        creates = self._creates
        
        for name, backend in backends:
            if not issubclass(backend.__class__, CreateFromEmailBackend):
                raise NotValidFromEmailCRUDBackend("%r has to subclass CreateFromEmailBackend" % backend)#assert ?
            
            if creates.has_key(name):
                if name == "*":
                    raise NotValidFromEmailCRUDBackend("Only one fallback backend allowed")
                else:
                    warning("Duplicate create CRUD backend or backend registered twice : %s", name) #exception instead ???
            creates[name] = backend

    def get_create(self, name):
        return self._creates.get(name)


    def get(self, type, key):
        return {
            CREATE: self.get_create
            
        }.get(type, lambda x:None)(key)

    def iteritems(self):
        return chain(self._creates.iteritems(),
                     self._reads.iteritems(),
                     self._updates.iteritems(),
                     self._delete.iteritems(),)

    def iter_creates_values(self):
        return self._creates.itervalues()

    def get_creates(self):
        return self._creates


from_email_crud_registry = FromEmailCRUDRegistry()

email_crud_imports = find_n_import("crudity_email_register", ['crud_register'])

for email_crud_import in email_crud_imports:
    for crud_name, to_register in email_crud_import.crud_register.items():
        from_email_crud_registry.register(crud_name, to_register)