################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2016-2025  Hybird
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
from collections import defaultdict
from collections.abc import Callable, Iterable
from os.path import basename
from typing import TYPE_CHECKING

from django.core.exceptions import PermissionDenied
from django.db.models import Model
from django.db.models.fields.files import FieldFile, FileField

from ..models import CremeEntity, FieldsConfig, FileRef
from ..utils.collections import ClassKeyedMap

if TYPE_CHECKING:
    from typing import Any, DefaultDict

    # Any is user ; PermissionDenied can be raised
    PermissionChecker = Callable[[Any, Model], None]
    BasenameBuilder = Callable[[Model, FileField, FieldFile], str]

logger = logging.getLogger(__name__)


def check_entity_permission(user, instance: Model) -> None:
    user.has_perm_to_view_or_die(instance)


def check_fileref_permission(user, instance: Model) -> None:
    if instance.user != user:
        raise PermissionDenied('You can not read this FileRef')


def check_app_permission(user, instance):
    user.has_perm_to_access_or_die(instance._meta.app_label)


class DownLoadableFileField:
    slots = ('field', 'file_obj', 'base_name')

    def __init__(self,
                 field: FileField,
                 file: FieldFile,
                 base_name: str):
        self.field = field
        self.file = file
        self.base_name = base_name


class FileFieldDownLoadRegistry:
    class InvalidField(Exception):
        pass

    class RegistrationError(Exception):
        pass

    class _Info:
        slots = ('field', 'permission_checker', 'basename_builder')

        def __init__(self,
                     field: FileField,
                     permission_checker: PermissionChecker,
                     basename_builder: BasenameBuilder):
            self.field = field
            self.permission_checker = permission_checker
            self.basename_builder = basename_builder

    def __init__(
            self, *,
            default_permission_checker: PermissionChecker = check_app_permission,
            permission_checkers: Iterable[tuple[Model, PermissionChecker]] = (
                (CremeEntity, check_entity_permission),
                (FileRef,     check_fileref_permission),
            )):
        self._models_fields: \
            DefaultDict[type[Model], dict[str, FileFieldDownLoadRegistry._Info]] \
            = defaultdict(dict)
        self.permission_checkers = ClassKeyedMap(
            permission_checkers,
            default=default_permission_checker,
        )

    def get(self, *,
            user,
            instance: Model,
            field_name: str) -> DownLoadableFileField:
        model = instance.__class__

        try:
            registered_fnames = self._models_fields[model]
        except KeyError:
            raise self.InvalidField(f'Model {model} is not registered.')

        info = registered_fnames.get(field_name)
        if info is None:
            raise self.InvalidField('This field is not registered')

        if not user.is_staff:
            info.permission_checker(user, instance)

        if FieldsConfig.objects.get_for_model(model).is_fieldname_hidden(field_name):
            raise self.InvalidField('This field is hidden')

        field = info.field
        file_obj = getattr(instance, field_name)

        return DownLoadableFileField(
            field=field,
            file=file_obj,
            base_name=info.basename_builder(instance, field, file_obj),
        )

    @staticmethod
    def _default_basename_builder(instance: Model,
                                  field: FileField,
                                  file_obj: FieldFile) -> str:
        return basename(file_obj.path) if file_obj else '??'

    def register(
            self, *,
            model: type[Model],
            field_name: str,
            permission_checker: PermissionChecker | None = None,
            basename_builder: BasenameBuilder | None = None,
    ) -> FileFieldDownLoadRegistry:
        """Register FileField which can be downloaded.
        @param model: Class inheriting django.db.models.
        @param field_name: Name of one FileField of the 'model'.
        @param permission_checker: a callable which takes the arguments (user, instance),
                & raises an exception (PermissionDenied should be the best one) if the
                file cannot be viewed by this user.
        @param basename_builder: a callable which takes the arguments (instance, field, file_obj),
               & return a string (the name of the field in attachment).
        @return 'self'.
        @raise InvalidField (given model-field is not a file field).
        @raise RegistrationError (registration is duplicated).
        """
        field = model._meta.get_field(field_name)

        if not isinstance(field, FileField):
            raise self.InvalidField(
                f'The field {model}.{field_name} is not a FileField.'
            )

        registered_fnames = self._models_fields[model]

        if field_name in registered_fnames:
            raise self.RegistrationError(
                f'The field {model}.{field_name} is already registered.'
            )

        if permission_checker is None:
            permission_checker = self.permission_checkers[model]
            assert permission_checker is not None

        registered_fnames[field_name] = self._Info(
            field=field,
            permission_checker=permission_checker,
            basename_builder=basename_builder or self._default_basename_builder,
        )

        return self

    def unregister(
            self,
            model: type[Model],
            *field_names: str) -> FileFieldDownLoadRegistry:
        registered_fnames = self._models_fields.get(model)

        if registered_fnames:
            for field_name in field_names:
                try:
                    del registered_fnames[field_name]
                except KeyError:
                    logger.warning(
                        '%s.unregister(): the field %s.%s is not registered.',
                        self.__class__.__name__, model, field_name,
                    )
        else:
            logger.warning(
                '%s.unregister(): the model %s is not registered.',
                self.__class__.__name__, model,
            )

        return self


filefield_download_registry = FileFieldDownLoadRegistry()
