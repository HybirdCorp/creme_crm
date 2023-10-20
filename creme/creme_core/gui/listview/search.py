################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2019-2023  Hybird
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

from django.db import models

import creme.creme_core.forms.listview as lv_form
from creme.creme_core.core import entity_cell
from creme.creme_core.core.function_field import FunctionField
from creme.creme_core.models import CremeEntity, CustomField
from creme.creme_core.utils.collections import ClassKeyedMap


class AbstractListViewSearchFieldRegistry:
    """Base class for registries building list-view search-fields (see <creme_core.forms.listview>)
    depending on EntityCells (see <creme_core.core.entity_cell>) & users.

    The idea is to have a tree of registries ; each node is calling the child node the
    most adapted to the given EntityCell.
    Classically the root registry is a ListViewSearchFieldRegistry which has a child
    for each type of cell (regular-field, custom-field…).

    The interface of this class is :
     - mainly the method 'get_field()'.
     - the method 'pretty()' for debugging purposes.
     - other methods are internal helpers for child classes.

    Nomenclature:
     - A "builder" is an object which can instantiate a ListViewSearchField ; so it can be:
        - A class of search-field
          (i.e. inheriting <creme_core.forms.listview.ListViewSearchField>).
        - An instance of a search-field registry class
          (i.e. inheriting <AbstractListViewSearchFieldRegistry>).
    """
    def get_field(self, *, cell: entity_cell.EntityCell, user, **kwargs):
        """Get an instance of (a class inheriting) <creme_core.forms.listview.ListViewSearchField>.

        @param cell: An instance of <core.entity_cell.EntityCell>.
        @param user: An instance of <django.contrib.auth.get_user_model()>.

        @return: An instance of <ListViewSearchField>.
        """
        return self._build_field(builder=None, cell=cell, user=user, **kwargs)

    def pretty(self, indent: int = 0):
        """Get a pretty string to analyze registered items.

        @param indent: Indentation level.
        @return: A string.
        """
        return ' ' * indent + f'{type(self).__name__}:'

    @staticmethod
    def _instantiate_builder(sfield_builder):
        """Helper method which instantiates a builder if it's needed (
        because it's a registry class).
        Useful to implement methods which accept either field class or registry class as argument.

        @param sfield_builder: A class inheriting <ListViewSearchField> or
               <AbstractListViewSearchFieldRegistry>.
        @return: A builder.
        """
        return sfield_builder() if hasattr(sfield_builder, 'get_field') else sfield_builder

    @staticmethod
    def _build_field(builder, cell: entity_cell.EntityCell, user, **kwargs):
        """Helper method which instantiate a search-field from a builder.
        Useful to implement the method "get_field()".

        @param builder: A builder instance, or None (meaning "void" search-field).
        @param cell: An instance of <core.entity_cell.EntityCell>.
        @param user: An instance of <django.contrib.auth.get_user_model()>.

        @return: An instance of <ListViewSearchField>
        """
        if builder is None:
            return lv_form.ListViewSearchField(cell=cell, user=user, **kwargs)

        get_field = getattr(builder, 'get_field', None)
        if get_field is not None:
            builder = get_field

        return builder(cell=cell, user=user, **kwargs)

    @staticmethod
    def _pretty_builder(builder, indent: int):
        pretty = getattr(builder, 'pretty', None)

        return '{indent}{module}.{cls}'.format(
            indent=' ' * indent,
            module=builder.__module__,
            cls=builder.__name__,
        ) if pretty is None else pretty(indent=indent)


class RegularRelatedFieldSearchRegistry(AbstractListViewSearchFieldRegistry):
    """Class of ListViewSearchFieldRegistry specialized for cells representing
    ForeignKeys & ManyToManyFields.

    The returned search-field can be customised depending on the model class
    referenced by the ForeignKey/ManyToManyField/...
    (e.g. for ForeignKey(MyAuxiliaryModel, ...) )
    The default field can be customised too (used when the related model has
    no specific search-field).
    """
    DEFAULT_MODELS = (
        (CremeEntity, lv_form.EntityRelatedField),
    )

    def __init__(self, default=lv_form.RegularRelatedField,
                 models_to_register=DEFAULT_MODELS,
                 ):
        self._builders_4_models = ClassKeyedMap(default=None)
        self.register_default(default)

        for model, builder in models_to_register:
            self.register_related_model(model=model, sfield_builder=builder)

    def builder_4_related_model(self, model: type[models.Model]):
        return self._builders_4_models[model]

    @property
    def default_builder(self):
        return self._default_builder

    def get_field(self, *, cell, user, **kwargs):
        assert isinstance(cell, entity_cell.EntityCellRegularField)

        model_field = cell.field_info[-1]
        return self._build_field(
            builder=(
                self._builders_4_models[model_field.remote_field.model]
                or self._default_builder
            ),
            cell=cell, user=user,
            **kwargs
        )

    def pretty(self, indent=0):
        indent_str = ' ' * indent
        res = '{indent}{name}:\n{indent}  Default:\n{default}\n{indent}  Models:'.format(
            indent=indent_str,
            name=type(self).__name__,
            default=self._pretty_builder(self._default_builder, indent=indent + 4),
        )

        models = self._builders_4_models
        if models:
            for model, builder in models.items():
                res += '\n{indent}    [{module}.{cls}]:\n{builder}'.format(
                    indent=indent_str,
                    module=model.__module__,
                    cls=model.__name__,
                    builder=self._pretty_builder(builder, indent=indent + 6),
                )
        else:
            res += f'\n{indent_str}    (empty)'

        return res

    def register_default(self, sfield_builder) -> RegularRelatedFieldSearchRegistry:
        self._default_builder = self._instantiate_builder(sfield_builder)

        return self

    def register_related_model(self, *,
                               model: type[models.Model],
                               sfield_builder,
                               ) -> RegularRelatedFieldSearchRegistry:
        self._builders_4_models[model] = self._instantiate_builder(sfield_builder)

        # TODO ?
        # if self._enums_4_fields.setdefault(field, enumerator_class) is not enumerator_class:
        #     raise self.RegistrationError(
        #         '_EnumerableRegistry: this field is already registered: {model}.{field}'.format(
        #             model=model.__name__, field=field_name,
        #         )
        #     )

        return self


# TODO: factorise with RegularRelatedFieldSearchRegistry ?
class RegularFieldSearchRegistry(AbstractListViewSearchFieldRegistry):
    """Class of ListViewSearchFieldRegistry specialized for cells representing
    model fields (CharField, BooleanField, ForeignKey...).

    The returned search-field can be customised depending on (from greater priority to lesser):
      - A model-field (e.g. the field "name" of your model <Book>).
      - The class of the model-field (e.g. fields which have class inheriting CharField).

    There is a special case for model-fields which have choices.
    """
    DEFAULT_REGISTRATIONS = (
        (models.CharField, lv_form.RegularCharField),
        (models.TextField, lv_form.RegularCharField),

        (models.IntegerField,              lv_form.RegularIntegerField),
        (models.PositiveIntegerField,      lv_form.RegularPositiveIntegerField),
        (models.PositiveSmallIntegerField, lv_form.RegularPositiveIntegerField),

        (models.FloatField,   lv_form.RegularFloatField),
        (models.DecimalField, lv_form.RegularDecimalField),

        (models.BooleanField, lv_form.RegularBooleanField),
        # (models.NullBooleanField, RegularBooleanField),

        (models.DateField, lv_form.RegularDateField),
        # (models.TimeField, ), TODO

        (models.ForeignKey,      RegularRelatedFieldSearchRegistry),
        (models.ManyToManyField, RegularRelatedFieldSearchRegistry),
        # (models.OneToOneField, RegularRelatedFieldSearchRegistry), TODO

        # (models.IPAddressField, ...)  # TODO: what about ?

        # TODO: needs JSONField management in the RDBMS...
        # (fields.DurationField, ),
        # (fields.DatePeriodField, ),

        # No search
        # (models.FileField, ),
        # (models.ImageField, ),
    )

    def __init__(self,
                 to_register=DEFAULT_REGISTRATIONS,
                 choice_sfield_builder=lv_form.RegularChoiceField,
                 ):
        self._builders_4_modelfields = {}
        self._builders_4_modelfieldtypes = ClassKeyedMap(default=None)
        self.register_choice_builder(choice_sfield_builder)

        for model_field_cls, builder in to_register:
            self.register_model_field_type(type=model_field_cls, sfield_builder=builder)

    def builder_4_model_field(self, *, model: type[models.Model], field_name: str):
        field = model._meta.get_field(field_name)
        return self._builders_4_modelfields.get(field)

    def builder_4_model_field_type(self, model_field: type[models.Field]):
        return self._builders_4_modelfieldtypes[model_field]

    @property
    def choice_builder(self):
        return self._choice_builder

    def get_field(self, *, cell, user, **kwargs):
        assert isinstance(cell, entity_cell.EntityCellRegularField)

        model_field = cell.field_info[-1]

        return self._build_field(
            builder=(
                self._builders_4_modelfields.get(model_field)
                or (
                    self._choice_builder
                    if model_field.choices else
                    self._builders_4_modelfieldtypes[type(model_field)]
                )
            ),
            cell=cell, user=user,
            **kwargs
        )

    def pretty(self, indent=0):
        indent_str = ' ' * indent
        res = '{indent}{name}:\n{indent}  Choice:\n{choice}\n{indent}  Field types:'.format(
            indent=indent_str,
            name=type(self).__name__,
            choice=self._pretty_builder(self._choice_builder, indent=indent + 4),
        )

        for field_type, builder in self._builders_4_modelfieldtypes.items():
            res += '\n{}    [{}.{}]:\n{}'.format(
                indent_str,
                field_type.__module__,
                field_type.__name__,
                self._pretty_builder(builder, indent=indent + 6),
            )

        res += f'\n{indent_str}  Fields:'
        modelfields = self._builders_4_modelfields
        if modelfields:
            for field, builder in modelfields.items():
                res += '\n{}    [{}]:\n{}'.format(
                    indent_str,
                    field,
                    self._pretty_builder(builder, indent=indent + 6),
                )
        else:
            res += f'\n{indent_str}    (empty)'

        return res

    def register_choice_builder(self, sfield_builder) -> RegularFieldSearchRegistry:
        self._choice_builder = self._instantiate_builder(sfield_builder)

        return self

    def register_model_field(self, *,
                             model: type[models.Model],
                             field_name: str,
                             sfield_builder,
                             ) -> RegularFieldSearchRegistry:
        field = model._meta.get_field(field_name)
        self._builders_4_modelfields[field] = self._instantiate_builder(sfield_builder)

        # TODO ?
        # if self._enums_4_fields.setdefault(field, enumerator_class) is not enumerator_class:
        #     raise self.RegistrationError(
        #         '_EnumerableRegistry: this field is already registered: {model}.{field}'.format(
        #             model=model.__name__, field=field_name,
        #         )
        #     )

        return self

    def register_model_field_type(self, *,
                                  type: type[models.Field],
                                  sfield_builder,
                                  ) -> RegularFieldSearchRegistry:
        self._builders_4_modelfieldtypes[type] = self._instantiate_builder(sfield_builder)

        return self


class CustomFieldSearchRegistry(AbstractListViewSearchFieldRegistry):
    """Class of ListViewSearchFieldRegistry specialized for cells representing
    <creme_core.models.CustomField>.

    The returned search-field can be customised depending on the type (STR, INT...)
    of CustomField.
    """
    DEFAULT_FIELDS = (
        (CustomField.INT,        lv_form.CustomIntegerField),
        (CustomField.FLOAT,      lv_form.CustomDecimalField),
        (CustomField.BOOL,       lv_form.CustomBooleanField),
        (CustomField.STR,        lv_form.CustomCharField),
        (CustomField.DATE,       lv_form.CustomDatetimeField),
        (CustomField.DATETIME,   lv_form.CustomDatetimeField),
        (CustomField.ENUM,       lv_form.CustomChoiceField),
        (CustomField.MULTI_ENUM, lv_form.CustomChoiceField),
    )

    # TODO: use an enum.IntEnum in CustomField
    __TYPES_ALIASES = {
        CustomField.INT:        'CustomField.INT',
        CustomField.FLOAT:      'CustomField.FLOAT',
        CustomField.BOOL:       'CustomField.BOOL',
        CustomField.STR:        'CustomField.STR',
        CustomField.DATE:       'CustomField.DATE',
        CustomField.DATETIME:   'CustomField.DATETIME',
        CustomField.ENUM:       'CustomField.ENUM',
        CustomField.MULTI_ENUM: 'CustomField.MULTI_ENUM',
    }

    def __init__(self, to_register=DEFAULT_FIELDS):
        self._builders = {}

        for cf_type, builder in to_register:
            self.register(type=cf_type, sfield_builder=builder)

    def builder(self, type):
        return self._builders.get(type)

    def get_field(self, *, cell, user, **kwargs):
        assert isinstance(cell, entity_cell.EntityCellCustomField)

        return self._build_field(
            builder=self._builders.get(cell.custom_field.field_type),
            cell=cell, user=user,
            **kwargs
        )

    def pretty(self, indent=0):
        indent_str = ' ' * indent
        res = f'{indent_str}{type(self).__name__}:'

        for cfield_type, builder in self._builders.items():
            res += '\n{}  [{}]:\n{}'.format(
                indent_str,
                self.__TYPES_ALIASES[cfield_type],
                self._pretty_builder(builder, indent=indent + 4),
            )

        return res

    def register(self, *, type: int, sfield_builder) -> CustomFieldSearchRegistry:
        self._builders[type] = self._instantiate_builder(sfield_builder)

        return self


class FunctionFieldSearchRegistry(AbstractListViewSearchFieldRegistry):
    """Class of ListViewSearchFieldRegistry specialized for cells representing
    <creme_core.core.function_field.FunctionField>.

    The returned search-field can be customised depending on the kind of FunctionField.
    """
    def __init__(self, to_register=()):
        self._builders = {}

        for ffield, builder in to_register:
            self.register(ffield=ffield, sfield_builder=builder)

    def builder(self, ffield: FunctionField):
        return self._builders.get(ffield.name)

    def get_field(self, *, cell, user, **kwargs):
        assert isinstance(cell, entity_cell.EntityCellFunctionField)

        ffield = cell.function_field

        return self._build_field(
            builder=(
                self._builders.get(ffield.name)
                or self._instantiate_builder(ffield.search_field_builder)
            ),
            cell=cell, user=user,
            **kwargs
        )

    def pretty(self, indent=0):
        indent_str = ' ' * indent
        res = f'{indent_str}{type(self).__name__}:'
        builders = self._builders

        if builders:
            for ffield_id, builder in builders.items():
                res += '\n{}  ["{}"]:\n{}'.format(
                    indent_str,
                    ffield_id,
                    self._pretty_builder(builder, indent=indent + 4),
                )
        else:
            res += f'\n{indent_str}  (empty)'

        return res

    def register(self, *,
                 ffield: FunctionField,
                 sfield_builder,
                 ) -> FunctionFieldSearchRegistry:
        self._builders[ffield.name] = self._instantiate_builder(sfield_builder)

        return self


class RelationSearchRegistry(AbstractListViewSearchFieldRegistry):
    """Class of ListViewSearchFieldRegistry specialized for cells representing RelationTypes.

    The returned search-field can be customised depending on the type ID ;
    a default field is returned when no specific one has been registered
    (the default builder can be set too).
    """
    def __init__(self, to_register=(), default=lv_form.RelationField):
        self._builders = {}
        self.register_default(default)

        for rtype_id, builder in to_register:
            self.register(rtype_id=rtype_id, sfield_builder=builder)

    def builder(self, rtype_id):
        return self._builders.get(rtype_id)

    @property
    def default_builder(self):
        return self._default_builder

    def get_field(self, *, cell, user, **kwargs):
        assert isinstance(cell, entity_cell.EntityCellRelation)

        return self._build_field(
            builder=self._builders.get(cell.relation_type.id, self._default_builder),
            cell=cell, user=user,
            **kwargs
        )

    def pretty(self, indent=0):
        indent_str = ' ' * indent
        res = '{indent}{name}:\n{indent}  Default:\n{default}'.format(
            indent=indent_str,
            name=type(self).__name__,
            default=self._pretty_builder(self._default_builder, indent=indent + 4),
        )

        for rtype_id, builder in self._builders.items():
            res += '\n{}  ["{}"]:\n{}'.format(
                indent_str,
                rtype_id,
                self._pretty_builder(builder, indent=indent + 4),
            )

        return res

    def register(self, *, rtype_id: str, sfield_builder) -> RelationSearchRegistry:
        self._builders[rtype_id] = self._instantiate_builder(sfield_builder)

        return self

    def register_default(self, sfield_builder) -> RelationSearchRegistry:
        self._default_builder = self._instantiate_builder(sfield_builder)

        return self


class ListViewSearchFieldRegistry(AbstractListViewSearchFieldRegistry):
    """Class of ListViewSearchFieldRegistry which has sub-registries for
    different types of EntityCell.
    """
    DEFAULT_REGISTRIES = (
        (entity_cell.EntityCellRegularField.type_id,  RegularFieldSearchRegistry),
        (entity_cell.EntityCellCustomField.type_id,   CustomFieldSearchRegistry),
        (entity_cell.EntityCellFunctionField.type_id, FunctionFieldSearchRegistry),
        (entity_cell.EntityCellRelation.type_id,      RelationSearchRegistry),
        # NB: not useful because volatile cells cannot be retrieved by HeaderFilter.cells()
        # (entity_cell.EntityCellVolatile.type_id, ...),
    )

    def __init__(self, to_register=DEFAULT_REGISTRIES):
        self._registries = {}

        for cell_id, registry_class in to_register:
            self.register(cell_id=cell_id, registry_class=registry_class)

    def __getitem__(self, cell_type_id: str):
        return self._registries[cell_type_id]

    def pretty(self, indent=0):
        indent_str = ' ' * indent
        res = f'{indent_str}{type(self).__name__}:'

        def get_alias(cell_id):
            try:
                cell_cls = entity_cell.CELLS_MAP[cell_id]
            except KeyError:
                return '??'

            return f'{cell_cls.__name__}.type_id'

        for cell_id, registry in self._registries.items():
            res += '\n{indent}  [{alias}="{id}"]:\n{registry}'.format(
                indent=indent_str,
                alias=get_alias(cell_id),
                id=cell_id,
                registry=registry.pretty(indent=indent + 4),
            )

        return res

    def get_field(self, *, cell, user, **kwargs):
        registry = self._registries.get(cell.type_id)

        return (
            super().get_field(cell=cell, user=user, **kwargs)
            if registry is None else
            registry.get_field(cell=cell, user=user, **kwargs)
        )

    def register(self, *, cell_id: str, registry_class) -> ListViewSearchFieldRegistry:
        self._registries[cell_id] = registry_class()

        return self


search_field_registry = ListViewSearchFieldRegistry()
