################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024-2025  Hybird
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

from collections.abc import Iterator

from django.db.transaction import atomic
from django.utils.translation import gettext as _

from creme.billing.models import Base
from creme.creme_core.core import copying
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.core.workflow import run_workflow_engine
from creme.creme_core.models import CremeUser


class Converter:
    """This class manages the conversion of billing entities to another.
     - is a user allowed to convert?
     - perform the conversion.

    Notice "conversion" does not mean we delete the source entities; indeed we
    just create a new instance.

    Hint: see class <ConverterRegistry>.
    """
    pre_save_copiers: list[type[copying.PreSaveCopier]] = []
    post_save_copiers: list[type[copying.PostSaveCopier]] = []

    def __init__(self, *, user: CremeUser, source: Base, target_model: type[Base]):
        """Constructor.
        @param user: Logger user who wants to perform the conversion.
        @param source: Instance we want to convert.
        @param target_model: Type of the new instance we want to create.
        """
        self._user = user
        self._source = source
        self._target_model = target_model

    @property
    def source(self):
        return self._source

    @property
    def target_model(self):
        return self._target_model

    @property
    def user(self):
        return self._user

    def _check_permissions_for_user(self) -> None:
        if self._user.is_staff:
            raise ConflictError(_('A staff user cannot convert.'))

    def _check_permissions_for_source(self) -> None:
        source = self._source
        self._user.has_perm_to_view_or_die(source)

        if source.is_deleted:
            raise ConflictError(
                _('This entity cannot be converted because it is deleted.')
            )

    def _check_permissions_for_target(self) -> None:
        self._user.has_perm_to_create_or_die(self._target_model)

    def check_permissions(self) -> None:
        """Checks if the given instance can be converted.
        If an exception is raised, the conversion is forbidden (the exception
        should contain the reason -- a translated human readable one).
        @raise PermissionDenied, ConflictError.
        """
        self._check_permissions_for_user()
        self._check_permissions_for_source()
        self._check_permissions_for_target()

    def _build_instance(self) -> Base:
        return self._target_model()

    def _pre_save(self, *, user, source, target) -> None:
        for copier_class in self.pre_save_copiers:
            copier_class(source=source, user=user).copy_to(target=target)

    def _post_save(self, *, user, source, target) -> bool:
        """@return: Should the target be saved again?"""
        save = False

        for copier_class in self.post_save_copiers:
            save |= bool(copier_class(source=source, user=user).copy_to(target=target))

        return save

    def perform(self) -> Base:
        """Performs the conversion."""
        converted = self._build_instance()
        user = self._user
        source = self._source

        with atomic(), run_workflow_engine(user=user):
            self._pre_save(user=user, source=source, target=converted)
            converted.save()
            if self._post_save(user=user, source=source, target=converted):
                converted.save()

        return converted


class ConverterRegistry:
    """Stores the conversion behaviours per Base sub-model."""
    class RegistrationError(Exception):
        pass

    class UnRegistrationError(RegistrationError):
        pass

    _converter_classes: dict[tuple[type[Base], type[Base]], type[Converter]]

    def __init__(self):
        self._converter_classes = {}

    def get_converter_class(self, *,
                            source_model: type[Base],
                            target_model: type[Base],
                            ) -> type[Converter] | None:
        return self._converter_classes.get((source_model, target_model))

    def get_converter(self, *,
                      user: CremeUser,
                      source: Base,
                      target_model: type[Base],
                      ) -> Converter | None:
        """Hint: if None is returned, you should not convert the instances of
        the given model.
        """
        cls = self.get_converter_class(
            source_model=type(source), target_model=target_model,
        )

        return None if cls is None else cls(
            user=user, source=source, target_model=target_model,
        )

    @property
    def models(self) -> Iterator[tuple[type[Base], type[Base]]]:
        """Returns tuples (source_models, target_models) corresponding to all
        registered converters.
        """
        yield from self._converter_classes.keys()

    def register(self, *,
                 source_model: type[Base],
                 target_model: type[Base],
                 converter_class=Converter,
                 ) -> ConverterRegistry:
        """Hint: register a child class of Converter if you want to
        customise the conversion behaviour.
        """
        if self._converter_classes.setdefault(
            (source_model, target_model),
            converter_class,
        ) is not converter_class:
            raise self.RegistrationError(
                f'({source_model.__name__}, {target_model.__name__}) has already a converter'
            )

        return self

    def unregister(self, *,
                   source_model: type[Base],
                   target_model: type[Base],
                   ) -> ConverterRegistry:
        try:
            del self._converter_classes[(source_model, target_model)]
        except KeyError as e:
            raise self.UnRegistrationError(
                f'({source_model.__name__}, {target_model.__name__}) has no '
                f'converter (not registered or already unregistered)'
            ) from e

        return self


converter_registry = ConverterRegistry()
