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

from django.contrib.auth.backends import ModelBackend

from . import STAFF_PERM, SUPERUSER_PERM
from .entity_credentials import EntityCredentials

_ADD_PREFIX = 'add_'
_EXPORT_PREFIX = 'export_'


class EntityBackend(ModelBackend):
    supports_object_permissions = True

    def has_perm(self, user_obj, perm, obj=None):
        if perm == STAFF_PERM:
            return user_obj.is_staff

        if perm == SUPERUSER_PERM:
            return user_obj.is_superuser

        if user_obj.is_superuser:
            return True

        if obj is not None:
            return EntityCredentials(user_obj, obj).has_perm(perm)

        if user_obj.role is not None:
            app_name, dot, action_name = perm.partition('.')

            if not action_name:
                return user_obj.has_perm_to_access(app_name)

            if action_name == 'can_admin':
                return user_obj.has_perm_to_admin(app_name)

            if action_name.startswith(_ADD_PREFIX):
                return user_obj.role.can_create(app_name, action_name[len(_ADD_PREFIX):])

            if action_name.startswith(_EXPORT_PREFIX):
                return user_obj.role.can_export(app_name, action_name[len(_EXPORT_PREFIX):])

        return False
