################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024  Hybird
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

# TODO: unit tests!!!!!!!!!!!!

from __future__ import annotations

from django.db.transaction import atomic
from django.utils.translation import gettext as _

from creme.billing.models import Base
from creme.creme_core.core import cloning  # TODO: only "Cloner"?
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import CremeEntity, CremeUser


class Converter:
    """ TODO
     This class manages the cloning of CremeEntities.
     - is a user allowed to clone?
     - perform the cloning.

    Hint: see class <EntityClonerRegistry>.
    """
    pre_save_copiers: list[type[cloning.Copier]] = [
        # CommonRegularFieldsCopier,
        # billing_cloners.SourceCopier,
        # billing_cloners.TargetCopier,
    ]
    post_save_copiers: list[type[cloning.Copier]] = [
        # ManyToManyFieldsCopier,
        # CustomFieldsCopier,
        # PropertiesCopier,
        # RelationsCopier,
    ]

    # def __init__(self, target_model):
    def __init__(self, *, user: CremeUser, source: Base, target_model: type[Base]):
        """TODO"""
        self._user = user
        self._source = source
        self._target_model = target_model

    # TODO: properties for _user, _source, _target_model

    # def check_permissions(self, *, user: CremeUser, entity: CremeEntity) -> None:
    #     """Checks if the given instance can be cloned.
    #     If an exception is raised, the cloning is forbidden (the exception
    #     should contain the reason -- a translated human readable one).
    #     @raise PermissionDenied, ConflictError.
    #     """
    #     if entity.is_deleted:
    #         raise ConflictError(_('A deleted entity cannot be cloned'))
    #
    #     user.has_perm_to_create_or_die(entity)
    #     user.has_perm_to_view_or_die(entity)

    def _check_permissions_for_user(self) -> None:
        if self._user.is_staff:
            raise ConflictError(_('A staff user cannot convert.'))

    def _check_permissions_for_source(self) -> None:
        source = self._source
        self._user.has_perm_to_view_or_die(source)

        # TODO: move to EntityRelatedMixin ??
        if source.is_deleted:
            raise ConflictError(
                _('This entity cannot be converted because it is deleted.')
            )

    def _check_permissions_for_target(self) -> None:
        self._user.has_perm_to_create_or_die(self._target_model)

    def check_permissions(self) -> None:
        """Checks if the given instance can be cloned.
        If an exception is raised, the cloning is forbidden (the exception
        should contain the reason -- a translated human readable one).
        @raise PermissionDenied, ConflictError.
        """
        self._check_permissions_for_user()
        self._check_permissions_for_source()
        self._check_permissions_for_target()

    def _build_instance(self) -> CremeEntity:
        return self._target_model()

    def _pre_save(self, *, user, source, target) -> None:
        for copier_class in self.pre_save_copiers:
            copier_class(source=source, user=user).copy_to(target=target)

    def _post_save(self, *, user, source, target) -> None:
        for copier_class in self.post_save_copiers:
            copier_class(source=source, user=user).copy_to(target=target)

    @atomic
    def perform(self) -> CremeEntity:
        """TODO
        Performs the cloning.

        @param user: the logged user (could be used by some custom cloner
               classes to make some check).
        @param entity: Instance to clone.
        """
        # converted = self._build_instance(user=user, source=entity)
        converted = self._build_instance()
        user = self._user
        source = self._source

        self._pre_save(user=user, source=source, target=converted)
        converted.save()
        self._post_save(user=user, source=source, target=converted)

        return converted


class ConverterRegistry:
    """TODO:
    Stores the cloning behaviours per CremeEntity model.
    """
    # TODO
    # class RegistrationError(Exception):
    #     pass
    #
    # class UnRegistrationError(RegistrationError):
    #     pass

    def __init__(self):
        self._converter_classes: dict[
            tuple[type[CremeEntity], type[CremeEntity]],
            type[Converter]
        ] = {}

    def get(self, *, user: CremeUser, source: Base, target_model: type[Base]) -> Converter | None:
        """TODO
        Hint: if None is returned, you should not clone the instances of
        the given model.
        """
        cls = self._converter_classes.get((type(source), target_model))

        return None if cls is None else cls(
            user=user, source=source, target_model=target_model,
        )

    @property
    def source_models(self):
        return {
            source_model for source_model, _target_model in self._converter_classes.keys()
        }

    def register(self,
                 source_model: type[CremeEntity],
                 target_model: type[CremeEntity],
                 converter_class=Converter,
                 ) -> ConverterRegistry:
        """TODO
        Hint: register a child class of EntityCloner if you want to
        customise the cloning behaviour.
        """
        # TODO
        # if self._cloner_classes.setdefault(model, cloner_class) is not cloner_class:
        #     raise self.RegistrationError(f'<{model.__name__}> has already a cloner')
        self._converter_classes[(source_model, target_model)] = converter_class

        return self

    # TODO
    # def unregister(self, model: type[CremeEntity]) -> EntityClonerRegistry:
    #     try:
    #         del self._cloner_classes[model]
    #     except KeyError as e:
    #         raise self.UnRegistrationError(
    #             f'<{model.__name__}> has no cloner (not registered or already unregistered)'
    #         ) from e
    #
    #     return self


converter_registry = ConverterRegistry()
