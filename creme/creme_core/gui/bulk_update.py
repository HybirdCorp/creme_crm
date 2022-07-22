# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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

from functools import partial
from itertools import chain
from typing import (
    TYPE_CHECKING,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
)

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Field, ForeignKey, Model
from django.urls import reverse

from ..core.entity_cell import (
    EntityCell,
    EntityCellCustomField,
    EntityCellRegularField,
)
from ..core.field_tags import FieldTag
from ..models import CremeEntity, CremeModel, CustomField, FieldsConfig
from ..utils.unicode_collation import collator

if TYPE_CHECKING:
    from ..forms.bulk import BulkForm

# TODO: factorise 'customfield-...'


class FieldNotAllowed(Exception):
    pass


class _BulkUpdateRegistry:
    """Registry which stores what fields of entities models can or cannot be
    edited via the inner/bulk edition system, and if they use a specific form.

    For the app writers, only the register() method should be useful. Call it in
    your creme_core_register.py with the global 'bulk_update_registry' instance.
    """
    class ModelBulkStatus:
        _model: Type[Model]
        ignore: bool

        excludes: Set[str]
        expandables: Set[str]

        _innerforms: Dict[str, Type['BulkForm']]
        _regularfields: Dict[str, Field]

        def __init__(self, model: Type[Model], ignore: bool = False):
            self._model = model
            self.ignore = ignore

            self.excludes = set()
            self.expandables = set()

            self._innerforms = {}
            self._regularfields = {}

        def _reset_cache(self) -> None:
            # self._regularfields = {}
            self._regularfields.clear()

        def is_expandable(self, field: Field) -> bool:
            # if not isinstance(field, ForeignKey) or field.get_tag('enumerable'):
            if not isinstance(field, ForeignKey) or field.get_tag(FieldTag.ENUMERABLE):
                return False

            return (
                issubclass(field.remote_field.model, CremeModel)
                or field.name in self.expandables
            )

        def is_updatable(self, field: Union[Field, CustomField]) -> bool:
            return (
                isinstance(field, CustomField)
                or (
                    field.editable
                    and not field.auto_created
                    and not FieldsConfig.objects
                                        .get_for_model(self._model)
                                        .is_field_hidden(field)
                )
            )

        @property
        def regular_fields(self) -> Dict[str, Field]:
            if self.ignore:
                return {}

            rfields = self._regularfields

            if not rfields:
                meta = self._model._meta
                self._regularfields = rfields = {
                    field.name: field
                    for field in chain(meta.fields, meta.many_to_many)
                    if field.name not in self.excludes
                }

            return rfields

        @property
        def updatable_regular_fields(self) -> Dict[str, Field]:
            # TODO: FieldsConfig.LocalCache ??
            is_updatable = self.is_updatable

            return {
                key: field
                for key, field in self.regular_fields.items()
                if is_updatable(field)
            }

        @property
        def expandable_regular_fields(self) -> Dict[str, Field]:
            is_expandable = self.is_expandable

            return {
                key: field
                for key, field in self.regular_fields.items()
                if is_expandable(field)
            }

        @property
        def custom_fields(self) -> Dict[str, CustomField]:
            if self.ignore:
                return {}

            model = self._model
            custom_fields = {
                f'customfield-{field.pk}': field
                for field in CustomField.objects.compatible(model).exclude(is_deleted=True)
            }

            for field in custom_fields.values():
                field.model = self._model

            return custom_fields

        def get_field(self, name: str) -> Union[Field, CustomField]:
            if name.startswith('customfield-'):
                field = self.custom_fields.get(name)
            else:
                field = self.regular_fields.get(name)

                if field and not self.is_updatable(field):
                    raise FieldNotAllowed(
                        f'The field {self._model._meta.verbose_name}.{name} is not editable'
                    )

            if field is None:
                raise FieldDoesNotExist(
                    f"The field {self._model._meta.verbose_name}.{name} doesn't exist"
                )

            return field

        def get_expandable_field(self, name: str) -> Field:
            field = self.regular_fields.get(name)

            if field is None:
                raise FieldDoesNotExist(
                    f"The field {self._model._meta.verbose_name}.{name} doesn't exist"
                )

            if not self.is_expandable(field):
                raise FieldNotAllowed(
                    f'The field {self._model._meta.verbose_name}.{name} is not expandable'
                )

            return field

        def get_form(self,
                     name: str,
                     default: Optional[Type['BulkForm']] = None,
                     ) -> Optional[Type['BulkForm']]:
            return self._innerforms.get(name, default)

    def __init__(self):
        self._status: Dict[Type[Model], _BulkUpdateRegistry.ModelBulkStatus] = {}

    def _get_or_create_status(self, model: Type[Model]) -> ModelBulkStatus:
        bulk_status = self._status.get(model)

        if bulk_status is None:
            bulk_status = self._status[model] = self.ModelBulkStatus(model)

        return bulk_status

    def _merge_innerforms(self,
                          parent_status: ModelBulkStatus,
                          child_status: ModelBulkStatus,
                          ) -> None:
        child_status._innerforms = {
            **parent_status._innerforms,
            **child_status._innerforms,
        }

    def register(self,
                 model: Type[Model],
                 exclude: Sequence[str] = (),
                 expandables: Sequence[str] = (),
                 innerforms: Optional[Mapping[str, Type['BulkForm']]] = None,
                 ) -> ModelBulkStatus:
        """Register a CremeEntity class.
        @param model: Class inheriting CremeEntity.
        @param exclude: A sequence of field names (ie: strings) indicating
               fields should not be inner-editable.
        @param expandables: A sequence of field names corresponding to ForeignKeys
               with inner-editable sub-fields (the FK must have the
               tag 'enumerable' too). It is only useful for
               FK related to models which are not inheriting CremeModel.
        @param innerforms: A dict with items (field_name, form_class) which provides
               some specific forms to use. The form_class should inherit
               from creme.creme_core.forms.bulk.BulkForm
               (generally BulkDefaultEditForm is a good choice).
        """
        bulk_status = self._get_or_create_status(model)

        if exclude:
            bulk_status.excludes.update(exclude)

        if expandables:
            bulk_status.expandables.update(expandables)

        if innerforms:
            bulk_status._innerforms.update(innerforms)

        # Manage child and parent classes
        for other_model, other_status in self._status.items():
            if other_model is not model:
                if issubclass(other_model, model):
                    # Registered subclass inherits exclusions of new model
                    other_status.excludes.update(bulk_status.excludes)
                    other_status.expandables.update(bulk_status.expandables)
                    self._merge_innerforms(parent_status=bulk_status, child_status=other_status)
                elif issubclass(model, other_model):
                    # New model inherits exclusions and custom forms of registered superclass
                    bulk_status.excludes.update(other_status.excludes)
                    bulk_status.expandables.update(other_status.expandables)
                    self._merge_innerforms(parent_status=other_status, child_status=bulk_status)

        bulk_status._reset_cache()

        return bulk_status

    def ignore(self, model: Type[Model]) -> ModelBulkStatus:
        bulk_status = self._get_or_create_status(model)
        bulk_status.ignore = True

        return bulk_status

    def status(self, model: Type[Model]) -> ModelBulkStatus:
        bulk_status = self._status.get(model)

        # Get excluded field by inheritance in case of working model is not registered yet
        if bulk_status is None:
            bulk_status = self.register(model)

        return bulk_status

    def get_default_field(self, model: Type[Model]) -> Field:
        fields = self.regular_fields(model)
        return fields[0]

    def get_field(self,
                  model: Type[Model],
                  field_name: str,
                  ) -> Union[Field, CustomField]:
        status = self.status(model)
        field_basename, _sep_, subfield_name = field_name.partition('__')

        if subfield_name:
            parent_field = status.get_expandable_field(field_basename)
            field = self.get_field(parent_field.remote_field.model, subfield_name)
        else:
            field = status.get_field(field_basename)

        return field

    # TODO: rename "(get_)form_class"
    def get_form(self,
                 model: Type[Model],
                 field_name: str,
                 default: Optional[Type['BulkForm']] = None,
                 ) -> Optional[Type['BulkForm']]:
        status = self.status(model)
        field_basename, _sep_, subfield_name = field_name.partition('__')

        if subfield_name:
            field = status.get_expandable_field(field_basename)
            substatus = self.status(field.remote_field.model)
            subfield = substatus.get_field(subfield_name)
            form = substatus.get_form(subfield_name, default)

            return partial(form, model=model, field=subfield, parent_field=field) if form else None

        field = status.get_field(field_basename)
        form = status.get_form(field_basename, default)
        return partial(form, model=model, field=field) if form else None

    def is_updatable(self,
                     model: Type[Model],
                     field_name: str,
                     exclude_unique: bool = True,
                     ) -> bool:
        try:
            field = self.get_field(model, field_name)
        except (FieldDoesNotExist, FieldNotAllowed):
            return False

        return not (exclude_unique and field.unique)

    def is_expandable(self,
                      model: Type[Model],
                      field_name: str,
                      exclude_unique: bool = True,
                      ) -> bool:
        try:
            field = self.status(model).get_expandable_field(field_name)
        except (FieldDoesNotExist, FieldNotAllowed):
            return False

        return not (exclude_unique and field.unique)

    def regular_fields(self,
                       model: Type[Model],
                       expand: bool = False,
                       exclude_unique: bool = True,
                       ) -> Union[List[Field], List[Tuple[Field, List[Field]]]]:
        sort_key = collator.sort_key

        status = self.status(model)
        is_updatable = status.is_updatable

        fields: Iterable[Field] = status.regular_fields.values()

        if exclude_unique:
            fields = [field for field in fields if not field.unique]

        if expand is True:
            related_fields = self.regular_fields
            is_expandable = status.is_expandable

            field_states = [
                (field, is_expandable(field), is_updatable(field))
                for field in fields
            ]

            exp_fields = [
                (
                    field,
                    related_fields(
                        model=field.remote_field.model, exclude_unique=exclude_unique,
                    )
                    if expandable else
                    None,
                )
                for field, expandable, updatable in field_states
                if expandable or updatable
            ]

            return sorted(exp_fields, key=lambda f: sort_key(f[0].verbose_name))

        return sorted(
            filter(is_updatable, fields),
            key=lambda f: sort_key(f.verbose_name)
        )

    def custom_fields(self, model: Type[Model]) -> List[CustomField]:
        sort_key = collator.sort_key
        return sorted(
            self.status(model).custom_fields.values(),
            key=lambda f: sort_key(f.name)
        )

    # TODO: better system which allow inner edit other type of cells?
    # TODO: remove "user" arg
    def inner_uri(self, cell: EntityCell, instance: Model, user) -> Optional[str]:
        uri = None

        if isinstance(cell, EntityCellRegularField):
            field_name = cell.field_info[0].name

            if self.is_updatable(instance.__class__, field_name, exclude_unique=False):
                ct = ContentType.objects.get_for_model(instance.__class__)
                uri = reverse(
                    'creme_core__inner_edition',
                    args=(ct.id, instance.id, field_name),
                )
        elif isinstance(cell, EntityCellCustomField):
            assert isinstance(instance, CremeEntity)

            uri = reverse(
                'creme_core__inner_edition',
                args=(instance.entity_type_id, instance.id, f'customfield-{cell.value}'),
            )

        return uri


bulk_update_registry = _BulkUpdateRegistry()
