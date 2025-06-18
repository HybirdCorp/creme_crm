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

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Q, QuerySet

if TYPE_CHECKING:
    from ..models import CremeEntity

VIEW_PERM   = 'creme_core.view_entity'
CHANGE_PERM = 'creme_core.change_entity'
DELETE_PERM = 'creme_core.delete_entity'
LINK_PERM   = 'creme_core.link_entity'
UNLINK_PERM = 'creme_core.unlink_entity'


class EntityCredentials:
    NONE   = 0
    # ADD    = 0b000001   # Useless...
    VIEW   = 0b000010
    CHANGE = 0b000100
    DELETE = 0b001000
    LINK   = 0b010000
    UNLINK = 0b100000

    _ALL_CREDS = 63

    _PERMS_MAP: dict[str, int] = {
        VIEW_PERM:   VIEW,
        CHANGE_PERM: CHANGE,
        DELETE_PERM: DELETE,
        LINK_PERM:   LINK,
        UNLINK_PERM: UNLINK,
    }

    class FilteringError(Exception):
        pass

    def _sandbox_is_allowed(self, sandbox, user) -> bool:
        if sandbox.role_id:
            return sandbox.role_id == user.role_id

        sb_user_id = sandbox.user_id

        if sb_user_id is not None:
            # NB: we use 'user.teams' rather than 'sandbox.user.teammates' because 'user' is
            #     generally the request user & so 'user.teams' is cached.
            return user.id == sb_user_id or any((sb_user_id == team.id) for team in user.teams)

        return False

    def __init__(self, user, entity: CremeEntity):
        """Constructor.
        @param user: <django.contrib.auth.get_user_model()> instance.
        @param entity: CremeEntity (or child class) instance.
        """
        from ..models import CremeEntity
        if not isinstance(entity, CremeEntity):
            raise TypeError(
                'EntityCredentials: the argument "entity" is not a CremeEntity '
                f'(currently "{entity}" is a {type(entity)}).'
            )

        if user.is_superuser:
            value = self._ALL_CREDS
        else:
            role = user.role
            assert role is not None

            sandbox = entity.sandbox

            if sandbox is None or self._sandbox_is_allowed(sandbox=sandbox, user=user):
                value = role.get_perms(user, entity)
            else:
                value = self.NONE

        self._value = value

    def __str__(self):
        return f'EntityCredentials(value="{self._value}")'

    def can_change(self) -> bool:
        return self.has_perm(CHANGE_PERM)

    def can_delete(self) -> bool:
        return self.has_perm(DELETE_PERM)

    def can_link(self) -> bool:
        return self.has_perm(LINK_PERM)

    def can_unlink(self) -> bool:
        return self.has_perm(UNLINK_PERM)

    def can_view(self) -> bool:
        return self.has_perm(VIEW_PERM)

    def has_perm(self, string_permission: str) -> bool:
        return bool(self._PERMS_MAP[string_permission] & self._value)

    @classmethod
    def _build_sandbox_Q(cls, user) -> Q:
        teams = user.teams
        user_q = (
            Q(sandbox__user__isnull=False, sandbox__user__in=[user, *teams])
            if teams else
            Q(sandbox__user__isnull=False, sandbox__user=user)
        )

        return Q(sandbox=None) | Q(sandbox__role__isnull=False, sandbox__role=user.role) | user_q

    @classmethod
    def filter(cls,
               user,
               queryset: QuerySet,
               perm: int = VIEW,
               ) -> QuerySet:
        """Filter a Queryset of CremeEntities by the credentials of a given user.
        Beware, the model class must be a child class of CremeEntity,
        but cannot be CremeEntity itself.

        @param user: A <django.contrib.auth.get_user_model()> instance.
        @param queryset: A Queryset on a CremeEntity inheriting model
               (better if not yet retrieved).
        @param perm: A combination of values in (VIEW, CHANGE, DELETE, LINK, UNLINK)
               E.g. 'DELETE', 'VIEW | CHANGE'
        @return: A new Queryset on the same model, more selective (not retrieved).
        """
        from creme.creme_core.models import CremeEntity

        model = queryset.model

        if not issubclass(model, CremeEntity) or model is CremeEntity:
            raise ValueError(
                'EntityCredentials.filter() takes a queryset on models '
                'inheriting CremeEntity, not CremeEntity directly.'
            )

        if not user.is_superuser:
            role = user.role
            assert role is not None

            queryset = role.filter(
                user=user, perm=perm,
                queryset=queryset.filter(cls._build_sandbox_Q(user)),
            )

        return queryset

    @classmethod
    def filter_entities(cls,
                        user,
                        queryset: QuerySet,
                        perm: int = VIEW,
                        as_model: type[CremeEntity] | None = None,
                        ) -> QuerySet:
        """Filter a Queryset of CremeEntities by the credentials of a given user.
        Beware, model class must be CremeEntity ; it cannot be a child class of
        CremeEntity.

        @param user: A <django.contrib.auth.get_user_model()> instance.
        @param queryset: A <Queryset> with model=CremeEntity
               (better if not yet retrieved).
        @param perm: A value in (VIEW, CHANGE, DELETE, LINK, UNLINK).
               If the argument "as_model" is not None, you can use a combination
               of values like 'VIEW | CHANGE'.
        @param as_model: A model inheriting CremeEntity, or None.
               If a model is given, all the entities in the queryset are
               filtered with the credentials for this model.
               BEWARE: you should probably use this feature only if the queryset
               is already filtered by its field 'entity_type'
               (to keep only entities of the right model, & so do not
               make mistakes with credentials).
        @return: A new Queryset on CremeEntity, more selective (not retrieved).
        @raise: ValueError if the "queryset" does not concern 'CremeEntity'.
        @raise: EntityCredentials.FilteringError if there is an EntityFilter,
                which cannot be used on CremeEntity, in the SetCredentials
                concerning the models of the allowed apps.
        """
        from ..models import CremeEntity

        if queryset.model is not CremeEntity:
            raise ValueError(
                'EntityCredentials.filter_entities() takes '
                'a queryset on CremeEntity, not an inheriting model.'
            )

        if not user.is_superuser:
            role = user.role
            assert role is not None

            queryset = role.filter_entities(
                user=user, perm=perm, as_model=as_model,
                queryset=queryset.filter(cls._build_sandbox_Q(user)),
            )

        return queryset
