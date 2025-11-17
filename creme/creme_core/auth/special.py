################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2025  Hybird
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

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterator

from . import _SPECIAL_PREFIX

logger = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class SpecialPermission:
    """This class allows to declare a special permission.
    A UserRole can store the permission (see <userRole.special_permissions>,
    & then the code can check if a user gets this permission (see
    <CremeUser.has_special_perm()>).

    Example:
        - my_app/auth.py
            from django.utils.translation import gettext_lazy as _

            from creme.creme_core.auth.special import SpecialPermission

            teaching = SpecialPermission(
                id='my_app-teaching', verbose_name='Teaching',
                description=_('Can get a classroom & teach to pupils'),
            )

        - my_app/apps.py
            # [...]

            class MyAppConfig(CremeAppConfig):
                # [...]
                def register_permissions(self, special_perm_registry):
                    from . import auth

                    special_perm_registry.register( auth.teaching)

        - my_app/views.py
            from creme.creme_core.views.generic import CheckedView

            from .auth import teaching

            class MyView(CheckedView):
                permissions = teaching.as_perm
    """
    id: str
    verbose_name: str
    description: str

    def __str__(self):
        return str(self.verbose_name)

    @property
    def as_perm(self) -> str:
        """Generate a string which can be use by the permission system.
        It means it can be used by <CremeUser.has_perm()>.
        """
        return _SPECIAL_PREFIX + self.id


class SpecialPermissionRegistry:
    """The registered SpecialPermission can be retrieved by their ID.

    See <CremeAppConfig.register_permissions()>.
    """
    class RegistrationError(Exception):
        pass

    class UnRegistrationError(RegistrationError):
        pass

    def __init__(self):
        self._perms = {}

    @property
    def permissions(self) -> Iterator[SpecialPermission]:
        yield from self._perms.values()

    def get_permission(self, perm_id: str) -> SpecialPermission | None:
        perm = self._perms.get(perm_id)
        if perm is None:
            logger.warning('Invalid special permission ID: %s', perm_id)

        return perm

    def register(self, *perms: SpecialPermission) -> SpecialPermissionRegistry:
        reg_perms = self._perms

        for perm in perms:
            perm_id = perm.id
            if not perm_id:
                raise self.RegistrationError(
                    f"SpecialPermission with empty id: {perm}",
                )
            if perm_id in reg_perms:
                raise self.RegistrationError(
                    f"SpecialPermission with duplicated id: {perm}",
                )

            reg_perms[perm_id] = perm

        return self

    def unregister(self, *perm_ids: str) -> None:
        reg_perms = self._perms

        for perm_id in perm_ids:
            if reg_perms.pop(perm_id, None) is None:
                raise self.UnRegistrationError(
                    f'Invalid permission ID "{perm_id}" (already unregistered?)'
                )


special_perm_registry = SpecialPermissionRegistry()
