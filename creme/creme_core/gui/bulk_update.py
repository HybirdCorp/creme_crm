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

from __future__ import annotations

# from functools import partial
from itertools import chain
from typing import Iterable, Iterator, Sequence, Type  # TYPE_CHECKING Mapping

from django import forms
# from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import (  # FieldDoesNotExist,
    NON_FIELD_ERRORS,
    ValidationError,
)
from django.db.models import Field, FileField, Model  # ForeignKey
from django.urls import reverse
from django.utils.translation import gettext as _

from ..core.entity_cell import (
    EntityCell,
    EntityCellCustomField,
    EntityCellRegularField,
)
# from ..core.field_tags import FieldTag
from ..forms import base
# from ..utils.unicode_collation import collator
from ..models import CremeEntity, CustomField, FieldsConfig  # CremeModel

# if TYPE_CHECKING:
#     from ..forms.bulk import BulkForm


class FieldNotAllowed(Exception):
    pass


class FieldOverrider:
    """In inner/bulk edition forms, this class is used to manage the model
    fields which cannot just be edited with their regular form-field & the
    ModelForm behaviour (i.e. the fields that you'd manage manually if you write
    a form class, with special initialisation code in <__init__()>, special
    validation code etc…).
    See the parameter "overriders" of <_BulkUpdateRegistry.register()>.
    """
    # Each FieldOverrider must declare at least one field which is overridden.
    # You can override several fields, which means :
    #   - If a user want to edit one of the overridden fields, the overrider is used.
    #   - If a user want to edit several of the fields overridden by the same
    #     overrider, only one overrider instance is created (& so only one
    #     form-field).
    # It's useful when several model-fields are constrained together, like a
    # field "category" & a field "sub_category" which must always be edited
    # together.
    field_names: Sequence[str] = ()

    def __init__(self, key: str):
        self._key = key  # Used as form-field name by the related form

    @property
    def key(self):
        return self._key

    # TODO: possibility to return None (ignore field? error?)?
    def formfield(self, instances: list[Model], user) -> forms.Field:
        """Build a form-field which can manage the fields which are overridden
        (see 'field_name').
        @param instances: The instances which are edited (one instance with
               inner-edition, several ones with bulk-update). It's useful for:
                - setting the initial value (particularly if there is only one instance).
                - building a smart form-field. For example in app "activities",
                  you cannot change the type of Unavailability, except if all
                  instances are Unavailability.
        @param user: Logged user.
        """
        raise NotImplementedError

    def post_clean_instance(self, *,
                            instance: Model,
                            value,
                            form: base.CremeModelForm,
                            ) -> None:
        """This method is called by the generated form after the instance has
        been cleaned.
        Use it to raise ValidationErrors & to store cleaned data in the concerned
        fields of the instance.
        @raise ValidationError.
        """
        pass

    # TODO?
    # def post_save_instance(self, *,
    #                        instance: Model,
    #                        value,
    #                        form: (CremeEntity)Form
    #                        ) -> bool:
    #     """This method is called by the generated form after the instance has been saved.
    #     @return: A boolean indicating if the instance should be saved again.
    #     """
    #     return False


# NB1: The previous version (i.e. 2.3 & before) could manage some regular fields
#      like 'billing_address__city' (subfield of "not enumerable" FK).
#      - it was only proposed for bulk-update, not inner edition (implementation bug probably).
#      - it could only update existing instance (e.g. it could not create Address
#        instance on the go).
#      - it seems it was not used by any-one (some big bugs were never reported
#        until I discovered them during the work on the new "multi-field" version).
#     Maybe this possibility will be back one day...
#     IDEA: manage overriders of the form "fk__subfield" which could control the
#           creation of the related instance + force a second save of the entity.
# NB2: the previous version accepted models which were not inheriting CremeEntity ;
#      the new version focus on CremeEntity, but maybe the possibility will be
#      back if it's useful.
class _BulkUpdateRegistry:
    """Registry which stores which fields of entities models can or cannot be
    edited via the inner/bulk edition system, and if they use a specific form.

    For the app writers, only the register() method should be useful. Call it in
    your creme_core_register.py with the global 'bulk_update_registry' instance.
    """
    class Error(Exception):
        pass

#     class ModelBulkStatus:
#         _model: Type[Model]
#         ignore: bool
#
#         excludes: Set[str]
#         expandables: Set[str]
#
#         _innerforms: Dict[str, Type['BulkForm']]
#         _regularfields: Dict[str, Field]
#
#         def __init__(self, model: Type[Model], ignore: bool = False):
#             self._model = model
#             self.ignore = ignore
#
#             self.excludes = set()
#             self.expandables = set()
#
#             self._innerforms = {}
#             self._regularfields = {}
#
#         def _reset_cache(self) -> None:
#             # self._regularfields = {}
#             self._regularfields.clear()
#
#         def is_expandable(self, field: Field) -> bool:
#             # if not isinstance(field, ForeignKey) or field.get_tag('enumerable'):
#             if not isinstance(field, ForeignKey) or field.get_tag(FieldTag.ENUMERABLE):
#                 return False
#
#             return (
#                 issubclass(field.remote_field.model, CremeModel)
#                 or field.name in self.expandables
#             )
#
#         def is_updatable(self, field: Union[Field, CustomField]) -> bool:
#             return (
#                 isinstance(field, CustomField)
#                 or (
#                     field.editable
#                     and not field.auto_created
#                     and not FieldsConfig.objects
#                                         .get_for_model(self._model)
#                                         .is_field_hidden(field)
#                 )
#             )
#
#         @property
#         def regular_fields(self) -> Dict[str, Field]:
#             if self.ignore:
#                 return {}
#
#             rfields = self._regularfields
#
#             if not rfields:
#                 meta = self._model._meta
#                 self._regularfields = rfields = {
#                     field.name: field
#                     for field in chain(meta.fields, meta.many_to_many)
#                     if field.name not in self.excludes
#                 }
#
#             return rfields
#
#         @property
#         def updatable_regular_fields(self) -> Dict[str, Field]:
#             is_updatable = self.is_updatable
#
#             return {
#                 key: field
#                 for key, field in self.regular_fields.items()
#                 if is_updatable(field)
#             }
#
#         @property
#         def expandable_regular_fields(self) -> Dict[str, Field]:
#             is_expandable = self.is_expandable
#
#             return {
#                 key: field
#                 for key, field in self.regular_fields.items()
#                 if is_expandable(field)
#             }
#
#         @property
#         def custom_fields(self) -> Dict[str, CustomField]:
#             if self.ignore:
#                 return {}
#
#             model = self._model
#             custom_fields = {
#                 f'customfield-{field.pk}': field
#                 for field in CustomField.objects.compatible(model).exclude(is_deleted=True)
#             }
#
#             for field in custom_fields.values():
#                 field.model = self._model
#
#             return custom_fields
#
#         def get_field(self, name: str) -> Union[Field, CustomField]:
#             if name.startswith('customfield-'):
#                 field = self.custom_fields.get(name)
#             else:
#                 field = self.regular_fields.get(name)
#
#                 if field and not self.is_updatable(field):
#                     raise FieldNotAllowed(
#                         f'The field {self._model._meta.verbose_name}.{name} is not editable'
#                     )
#
#             if field is None:
#                 raise FieldDoesNotExist(
#                     f"The field {self._model._meta.verbose_name}.{name} doesn't exist"
#                 )
#
#             return field
#
#         def get_expandable_field(self, name: str) -> Field:
#             field = self.regular_fields.get(name)
#
#             if field is None:
#                 raise FieldDoesNotExist(
#                     f"The field {self._model._meta.verbose_name}.{name} doesn't exist"
#                 )
#
#             if not self.is_expandable(field):
#                 raise FieldNotAllowed(
#                     f'The field {self._model._meta.verbose_name}.{name} is not expandable'
#                 )
#
#             return field
#
#         def get_form(self,
#                      name: str,
#                      default: Optional[Type['BulkForm']] = None,
#                      ) -> Optional[Type['BulkForm']]:
#             return self._innerforms.get(name, default)

    class _ModelConfig:
        fields_considered_as_unique = (
            # NB1: it's probably a bad idea to set the same file to several entities
            #      (when one entity is deleted the file is attached to a FileRef then by a Job).
            # TODO: check if it's still true ; fix that?
            # NB2: bulk update of file field is broken on JS side any way(IDs are not posted ?)
            FileField,
        )

        def __init__(self, model: type[CremeEntity]):
            self._model: type[CremeEntity] = model
            self._excluded_fields: set[str] = set()
            self._overrider_classes: list[type[FieldOverrider]] = []

        def is_custom_field_updatable(self, cfield: CustomField) -> bool:
            return not cfield.is_deleted

        def is_regular_field_updatable(self,
                                       model: type[CremeEntity],
                                       field: Field,
                                       exclude_unique: bool = True,
                                       ) -> bool:
            return (
                field.editable
                and not field.auto_created
                and not (
                    exclude_unique and (
                        field.unique or isinstance(field, self.fields_considered_as_unique)
                    )
                )
                and field.name not in self._excluded_fields
                and not FieldsConfig.objects.get_for_model(model).is_field_hidden(field)
            )

        def regular_fields(self, exclude_unique: bool = True) -> Iterator[Field]:
            model = self._model
            meta = model._meta

            for field in chain(meta.fields, meta.many_to_many):
                if self.is_regular_field_updatable(
                    model=model, field=field, exclude_unique=exclude_unique,
                ):
                    yield field

        @property
        def custom_fields(self) -> Iterator[CustomField]:
            for cfield in CustomField.objects.get_for_model(self._model).values():
                if self.is_custom_field_updatable(cfield):
                    yield cfield

        # TODO: manage inheritance?
        #      (e.g. if 'user' is excluded in CremeEntity's config, it is
        #       excluded in Document's config automatically)
        def exclude(self, *field_names: str) -> _BulkUpdateRegistry._ModelConfig:
            """Indicate that some regular model fields cannot be edited.
            @param field_names: Names (string) of the fields to exclude.
            @return: The 'self' instance to allow chained calls.
            """
            # TODO: factorise
            overridden = {
                field_name
                for overrider_cls in self._overrider_classes
                for field_name in overrider_cls.field_names
            }
            for field_name in field_names:
                if field_name in overridden:
                    raise _BulkUpdateRegistry.Error(
                        f'The field "{field_name}" cannot be excluded & '
                        f'overridden at the same time.'
                    )

            self._excluded_fields.update(field_names)

            return self

        # TODO: manage inheritance?
        #      (e.g. if 'user' is overridden in CremeEntity's config, it is
        #       overridden in Document's config automatically)
        def add_overriders(self,
                           *overriders: type[FieldOverrider],
                           ) -> _BulkUpdateRegistry._ModelConfig:
            """
            Indicates that some regular model fields should not use their natural
            form-field, & use instead a specific form-field.

            See 'FieldOverrider'.

            @param overriders: Classes inheriting <FieldOverrider>.
            @return: The 'self' instance to allow chained calls.
            """
            # TODO: invalid field => error?
            excluded = self._excluded_fields
            already_overridden = {
                field_name
                for overrider_cls in self._overrider_classes
                for field_name in overrider_cls.field_names
            }
            for overrider_cls in overriders:
                for field_name in overrider_cls.field_names:
                    if field_name in excluded:
                        raise _BulkUpdateRegistry.Error(
                            f'The field "{field_name}" cannot be excluded & '
                            f'overridden at the same time.'
                        )

                    if field_name in already_overridden:
                        raise _BulkUpdateRegistry.Error(
                            f'The field "{field_name}" cannot be overridden several times.'
                        )
                    already_overridden.add(field_name)

            self._overrider_classes.extend(overriders)

            return self

        @property
        def overrider_classes(self) -> dict[str, Type[FieldOverrider]]:
            overrider_classes = {}
            for overrider_cls in self._overrider_classes:
                for field_name in overrider_cls.field_names:
                    overrider_classes[field_name] = overrider_cls

            return overrider_classes

    def __init__(self):
        # self._status: dict[type[Model], _BulkUpdateRegistry.ModelBulkStatus] = {}
        self._configs: dict[type[CremeEntity], _BulkUpdateRegistry._ModelConfig] = {}

    # def _get_or_create_status(self, model: type[Model]) -> ModelBulkStatus:
    #     bulk_status = self._status.get(model)
    #
    #     if bulk_status is None:
    #         bulk_status = self._status[model] = self.ModelBulkStatus(model)
    #
    #     return bulk_status

    # def _merge_innerforms(self,
    #                       parent_status: ModelBulkStatus,
    #                       child_status: ModelBulkStatus,
    #                       ) -> None:
    #     child_status._innerforms = {
    #         **parent_status._innerforms,
    #         **child_status._innerforms,
    #     }

    # def register(self,
    #              model: Type[Model],
    #              exclude: Sequence[str] = (),
    #              expandables: Sequence[str] = (),
    #              innerforms: Optional[Mapping[str, Type['BulkForm']]] = None,
    #              ) -> ModelBulkStatus:
    #     bulk_status = self._get_or_create_status(model)
    #
    #     if exclude:
    #         bulk_status.excludes.update(exclude)
    #
    #     if expandables:
    #         bulk_status.expandables.update(expandables)
    #
    #     if innerforms:
    #         bulk_status._innerforms.update(innerforms)
    #
    #     # Manage child and parent classes
    #     for other_model, other_status in self._status.items():
    #         if other_model is not model:
    #             if issubclass(other_model, model):
    #                 # Registered subclass inherits exclusions of new model
    #                 other_status.excludes.update(bulk_status.excludes)
    #                 other_status.expandables.update(bulk_status.expandables)
    #                 self._merge_innerforms(parent_status=bulk_status, child_status=other_status)
    #             elif issubclass(model, other_model):
    #                 # New model inherits exclusions and custom forms of registered superclass
    #                 bulk_status.excludes.update(other_status.excludes)
    #                 bulk_status.expandables.update(other_status.expandables)
    #                 self._merge_innerforms(parent_status=other_status, child_status=bulk_status)
    #
    #     bulk_status._reset_cache()
    #
    #     return bulk_status
    def register(self, model: type[CremeEntity]) -> _ModelConfig:
        """Register a CremeEntity class.
        @param model: Class inheriting CremeEntity.
        @return The instance of _ModelConfig which just has been created &
                registered. useful to call 'exclude()' & 'add_overriders()'.
        """
        if model in self._configs:
            raise _BulkUpdateRegistry.Error(
                f'The model "{model}" is already registered.'
            )

        self._configs[model] = config = self._ModelConfig(model)

        return config

    # def ignore(self, model: type[Model]) -> ModelBulkStatus:
    #     bulk_status = self._get_or_create_status(model)
    #     bulk_status.ignore = True
    #
    #     return bulk_status

    # def status(self, model: type[Model]) -> ModelBulkStatus:
    #     bulk_status = self._status.get(model)
    #
    #     # Get excluded field by inheritance in case of working model is not registered yet
    #     if bulk_status is None:
    #         bulk_status = self.register(model)
    #
    #     return bulk_status
    def config(self, model: type[CremeEntity]) -> _ModelConfig | None:
        return self._configs.get(model)

    # def get_default_field(self, model: type[Model]) -> Field:
    #     fields = self.regular_fields(model)
    #     return fields[0]

    # def get_field(self,
    #               model: type[Model],
    #               field_name: str,
    #               ) -> Field | CustomField:
    #     status = self.status(model)
    #     field_basename, _sep_, subfield_name = field_name.partition('__')
    #
    #     if subfield_name:
    #         parent_field = status.get_expandable_field(field_basename)
    #         field = self.get_field(parent_field.remote_field.model, subfield_name)
    #     else:
    #         field = status.get_field(field_basename)
    #
    #     return field

    # def get_form(self,
    #              model: type[Model],
    #              field_name: str,
    #              default: type[BulkForm] | None = None,
    #              ) -> type[BulkForm] | None:
    #     status = self.status(model)
    #     field_basename, _sep_, subfield_name = field_name.partition('__')
    #
    #     if subfield_name:
    #         field = status.get_expandable_field(field_basename)
    #         substatus = self.status(field.remote_field.model)
    #         subfield = substatus.get_field(subfield_name)
    #         form = substatus.get_form(subfield_name, default)
    #
    #         return partial(
    #             form, model=model, field=subfield, parent_field=field,
    #         ) if form else None
    #
    #     field = status.get_field(field_basename)
    #     form = status.get_form(field_basename, default)
    #     return partial(form, model=model, field=field) if form else None
    def build_form_class(self,
                         model: Type[CremeEntity],
                         cells: Sequence[EntityCell],
                         exclude_unique=False,
                         ) -> Type[base.CremeModelForm]:
        """Build a class inheriting <CremeModelForm> to edit only the given fields
        @param model: Type of the instance(s) we want to edit.
        @param cells: The EntityCells corresponding to the fields (regular fields,
               CustomFields) we want to edit.
        @return: The form class.
        @raise _BulkUpdateRegistry.Error (model not registered, not editable field...).

        Note about the behaviour of the generated form class:
        if you edit the field A of an instance, the field B is configured to
        be REQUIRED, and the field B is not filled for the instance. A ValidationError
        will be risen by the model's clean() method, and this error will be
        converted as a non-field-error.
        But CustomFields which are required & not filled will not cause error
        when you edit another field(s); it seems to be the less annoying behavior,
        but it could change if the future.
        """
        assert issubclass(model, CremeEntity)

        config = self._configs.get(model)
        if config is None:
            raise self.Error(
                f'The model "{model.__name__}" is not registered for inner-edition.'
            )

        if not cells:
            raise self.Error('Empty list of field/custom-field.')

        overrider_classes = config.overrider_classes

        field_names: list[str] = []
        cfields: list[CustomField] = []
        overriders: list[FieldOverrider] = []

        for cell in cells:
            if isinstance(cell, EntityCellRegularField):
                field_info = cell.field_info

                if len(field_info) > 1:
                    raise self.Error(
                        _(
                            'The field «{}» is not editable (it seems to be a sub-field).'
                        ).format(cell.title),
                    )

                if not config.is_regular_field_updatable(
                    model=model, field=field_info[0], exclude_unique=exclude_unique,
                ):
                    raise self.Error(
                        _(
                            'The field «{}» is not editable (it may have been hidden).'
                        ).format(cell.title),
                    )

                field_name = cell.value
                overrider_cls = overrider_classes.get(field_name)
                if overrider_cls is not None:
                    if not any(
                        field_name in used_overrider.field_names
                        for used_overrider in overriders
                    ):
                        overriders.append(overrider_cls(key=f'override-{field_name}'))
                else:
                    field_names.append(field_name)
            elif isinstance(cell, EntityCellCustomField):
                cfield = cell.custom_field

                if cfield.is_deleted:
                    raise self.Error(f'The field "{cfield.name}" is deleted')

                cfields.append(cfield)
            else:
                raise self.Error(f'The cell "{cell}" is not editable')

        # TODO: custom-fields only when entity?
        class InnerEditionForm(base.CustomFieldsMixin, base.CremeModelForm):
            def __init__(this, instances=(), *args, **kwargs):
                super().__init__(*args, **kwargs)
                # assert isinstance(self.instance, CremeEntity) TODO?
                this._build_customfields()

                for overrider in overriders:
                    this.fields[overrider.key] = overrider.formfield(
                        instances=instances or [this.instance], user=this.user,
                    )

            def _build_required_fields(self):
                # NB: we do not inject the field configured to be required ;
                #     the view display a link to the full form if a validation
                #     error is raised.
                # TODO: inject the fields if there is only one entity & the
                #       required fields are not filled?
                for field_name in self.fields_configs.get_for_model(model).required_field_names:
                    if field_name in field_names:
                        # TODO: KeyError is possible?
                        self.fields[field_name].required = True

            def _get_customfields_n_values(this, only_required):
                entity = this.instance
                CremeEntity.populate_custom_values([entity], cfields)

                return [
                    (cfield, entity.get_custom_value(cfield))
                    for cfield in cfields
                ]

            def clean(this):
                cleaned_data = super().clean()

                instance = this.instance
                get_data = this.cleaned_data.get

                for overrider in overriders:
                    key = overrider.key

                    try:
                        overrider.post_clean_instance(
                            instance=instance, value=get_data(key), form=this,
                        )
                    except ValidationError as e:
                        # TODO: remove wrapping if not ModelForm anymore?
                        this.add_error(key, e)

                return cleaned_data

            def save(this, *args, **kwargs):
                instance = super().save(*args, **kwargs)
                this._save_customfields()

                return instance

            def _update_errors(this, errors):
                # NB: some models can raise ValidationError related to some of their fields
                #     in their clean() method (e.g. documents.models.AbstractFolder).
                #     If one of this field does not correspond to any field in the form,
                #     the base form class raise a ValueError (& so we get an error 500).
                #     So here we remap these errors.

                error_dict = getattr(errors, 'error_dict', None)
                if error_dict:
                    keys_to_remap = [
                        field
                        for field in error_dict.keys()
                        if field != NON_FIELD_ERRORS and field not in this.fields
                    ]

                    for key in keys_to_remap:
                        messages = error_dict.pop(key)
                        # TODO: try to remap overridden fields instead of simply
                        #       transform them into non-field errors?
                        error_dict.setdefault(NON_FIELD_ERRORS, []).extend(messages)

                super()._update_errors(errors)

        cls = forms.modelform_factory(
            model, form=InnerEditionForm, fields=field_names,
        )

        return cls

    # def is_updatable(self,
    #                  model: type[Model],
    #                  field_name: str,
    #                  exclude_unique: bool = True,
    #                  ) -> bool:
    #     try:
    #         field = self.get_field(model, field_name)
    #     except (FieldDoesNotExist, FieldNotAllowed):
    #         return False
    #
    #     return not (exclude_unique and field.unique)

    # def is_expandable(self,
    #                   model: type[Model],
    #                   field_name: str,
    #                   exclude_unique: bool = True,
    #                   ) -> bool:
    #     try:
    #         field = self.status(model).get_expandable_field(field_name)
    #     except (FieldDoesNotExist, FieldNotAllowed):
    #         return False
    #
    #     return not (exclude_unique and field.unique)

    # def regular_fields(self,
    #                    model: type[Model],
    #                    expand: bool = False,
    #                    exclude_unique: bool = True,
    #                    ) -> list[Field] | list[tuple[Field, list[Field]]]:
    #     sort_key = collator.sort_key
    #
    #     status = self.status(model)
    #     is_updatable = status.is_updatable
    #
    #     fields: Iterable[Field] = status.regular_fields.values()
    #
    #     if exclude_unique:
    #         fields = [field for field in fields if not field.unique]
    #
    #     if expand is True:
    #         related_fields = self.regular_fields
    #         is_expandable = status.is_expandable
    #
    #         field_states = [
    #             (field, is_expandable(field), is_updatable(field))
    #             for field in fields
    #         ]
    #
    #         exp_fields = [
    #             (
    #                 field,
    #                 related_fields(
    #                     model=field.remote_field.model, exclude_unique=exclude_unique,
    #                 )
    #                 if expandable else
    #                 None,
    #             )
    #             for field, expandable, updatable in field_states
    #             if expandable or updatable
    #         ]
    #
    #         return sorted(exp_fields, key=lambda f: sort_key(f[0].verbose_name))
    #
    #     return sorted(
    #         filter(is_updatable, fields),
    #         key=lambda f: sort_key(f.verbose_name)
    #     )

    # def custom_fields(self, model: type[Model]) -> list[CustomField]:
    #     sort_key = collator.sort_key
    #     return sorted(
    #         self.status(model).custom_fields.values(),
    #         key=lambda f: sort_key(f.name)
    #     )

    # TODO: better system which allows inner edit other types of cell?
    # def inner_uri(self, cell: EntityCell, instance: Model, user) -> str | None:
    #     uri = None
    #
    #     if isinstance(cell, EntityCellRegularField):
    #         field_name = cell.field_info[0].name
    #
    #         if self.is_updatable(instance.__class__, field_name, exclude_unique=False):
    #             ct = ContentType.objects.get_for_model(instance.__class__)
    #             uri = reverse(
    #                 'creme_core__inner_edition',
    #                 args=(ct.id, instance.id, field_name),
    #             )
    #     elif isinstance(cell, EntityCellCustomField):
    #         assert isinstance(instance, CremeEntity)
    #
    #         uri = reverse(
    #             'creme_core__inner_edition',
    #             args=(instance.entity_type_id, instance.id, f'customfield-{cell.value}'),
    #         )
    #
    #     return uri
    def inner_uri(self, *, instance: CremeEntity, cells: Iterable[EntityCell]) -> str | None:
        from ..views.entity import InnerEdition

        model = type(instance)

        config = self.config(model)
        if config is None:
            return None

        cell_keys = []

        for cell in cells:
            if isinstance(cell, EntityCellRegularField):
                field_info = cell.field_info

                # TODO: manage len(field_info) > 1
                if len(field_info) != 1 or not config.is_regular_field_updatable(
                    model=model,
                    field=field_info[0],
                    exclude_unique=False,
                ):
                    continue
            elif isinstance(cell, EntityCellCustomField):
                if not config.is_custom_field_updatable(cell.custom_field):
                    continue
            else:
                continue

            cell_keys.append(cell.key)

        if not cell_keys:
            return None

        arg = InnerEdition.cell_key_arg

        return '{}?{}'.format(
            reverse(
                'creme_core__inner_edition',
                # NB: ContentType.objects.get_for_model(model).id if other model are allowed...
                args=(instance.entity_type_id, instance.id),
            ),
            '&'.join(f'{arg}={key}' for key in cell_keys),
        )


bulk_update_registry = _BulkUpdateRegistry()
