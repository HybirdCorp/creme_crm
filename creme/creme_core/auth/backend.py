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

from django.contrib.auth.backends import ModelBackend
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext as _

from . import (
    _CREATION_PREFIX,
    _EXPORT_PREFIX,
    _LINK_PREFIX,
    _LIST_PREFIX,
    _SPECIAL_PREFIX,
    STAFF_PERM,
    SUPERUSER_PERM,
)
from .entity_credentials import EntityCredentials
from .special import special_perm_registry


class EntityBackend(ModelBackend):
    supports_object_permissions = True

    def has_perm(self, user_obj, perm, obj=None):
        if perm == STAFF_PERM:
            if user_obj.is_staff:
                return True

            raise PermissionDenied(_('A staff user is required.'))

        if perm == SUPERUSER_PERM:
            if user_obj.is_superuser:
                return True

            raise PermissionDenied(_('A superuser is required.'))

        if user_obj.is_superuser:
            return True

        if obj is not None:
            # TODO: has_perm_or_die()
            return EntityCredentials(user_obj, obj).has_perm(perm)

        if user_obj.role is not None:
            if perm.startswith(_SPECIAL_PREFIX):
                perm = special_perm_registry.get_permission(
                    perm.removeprefix(_SPECIAL_PREFIX)
                )
                if perm is None:
                    return False

                user_obj.has_special_perm_or_die(perm)
                return True

            app_label, dot, action_name = perm.partition('.')

            if not action_name:
                user_obj.has_perm_to_access_or_die(app_label)
                return True

            if action_name == 'can_admin':
                user_obj.has_perm_to_admin_or_die(app_label)
                return True

            if action_name.startswith(_CREATION_PREFIX):
                ct = ContentType.objects.get_by_natural_key(
                    app_label=app_label,
                    model=action_name.removeprefix(_CREATION_PREFIX),
                )
                user_obj.has_perm_to_create_or_die(ct)
                return True

            if action_name.startswith(_LINK_PREFIX):
                ct = ContentType.objects.get_by_natural_key(
                    app_label=app_label,
                    model=action_name.removeprefix(_LINK_PREFIX),
                )
                user_obj.has_perm_to_link_or_die(ct.model_class())  # TODO: accept ContentType
                return True

            if action_name.startswith(_LIST_PREFIX):
                ct = ContentType.objects.get_by_natural_key(
                    app_label=app_label,
                    model=action_name[len(_LIST_PREFIX):],
                )
                user_obj.has_perm_to_list_or_die(ct)
                return True

            if action_name.startswith(_EXPORT_PREFIX):
                ct = ContentType.objects.get_by_natural_key(
                    app_label=app_label,
                    model=action_name.removeprefix(_EXPORT_PREFIX),
                )
                user_obj.has_perm_to_export_or_die(ct)
                return True

        return False
