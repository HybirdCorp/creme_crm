################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2026  Hybird
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
import warnings
from collections.abc import Iterable
from functools import partial
from typing import Self, override

from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.db.models import Field, Model
from django.db.models.expressions import BaseExpression

from creme.creme_core.core.entity_cell import (
    CELLS_MAP,
    EntityCell,
    EntityCellCustomField,
    EntityCellFunctionField,
    EntityCellRegularField,
)
from creme.creme_core.core.function_field import FunctionField
from creme.creme_core.models import CremeEntity, CustomField, fields
from creme.creme_core.utils.collections import ClassKeyedMap
from creme.creme_core.utils.db import get_indexed_ordering
from creme.creme_core.utils.meta import Order, OrderedField

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# TODO: fix docstring
# TODO: unit test
class QuerySortInfo:
    """Information on how to sort (i.e. order_by()) a Query(Set).

    It contains 3 attributes:
        - main_cell_key: the key of the EntityCell used as main ordering "field" (string).
        - main_order: instance of <creme_core.utils.meta.Order>. Order of the main ordering field.
        - field_names: tuple of strings. Can be used as order_by() arguments.
    """
    main_cell_key: str | None
    main_order: Order
    field_names: tuple[str, ...]

    def __init__(self,
                 cell_key: str | None,
                 order: Order, field_names: tuple[str, ...] = (),
                 orm_annotations=None,  # TODO: typing
                 ):
        self.main_cell_key = cell_key
        self.main_order = order
        self.field_names = field_names
        self.annotations = orm_annotations  # TODO: "frozen dict"

    def __repr__(self):
        return (
            f'QuerySortInfo('
            f'cell_key={self.main_cell_key!r}, '
            f'order={self.main_order!r}, '
            f'field_names={self.field_names!r}'
            # f'annotations={self.annotations!r}'  TODO?
            f')'
        )


# ------------------------------------------------------------------------------
# TODO: unit test
class SortingItem:
    """Represents a "columns" in an SQL ordering sequence."""
    def __init__(self, *, model: type[Model], name: str):
        self._model = model
        self._name = name
        self._db_expression: BaseExpression | None = None

    @property
    def db_expression(self) -> BaseExpression | None:
        """DB expression (see 'django.db.models.expressions') use to compute
        this column (if it's an annotation).
        @return <None> if no expressions is used.
        """
        return self._db_expression

    @property
    def model(self) -> type[Model]:
        return self._model

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_unique(self) -> bool:
        """Is the related column unique in the related table."""
        return False


class RegularFieldSortingItem(SortingItem):
    """Ordering with a true model field.
    Here the attribute "name" is the field's name.
    """
    @property
    def is_unique(self) -> bool:
        try:
            field = self._model._meta.get_field(self._name)
        except FieldDoesNotExist:
            return False

        return field.unique


class AnnotationSortingItem(SortingItem):
    """Ordering with an annotation (see <QuerySet.annotatae()>).
    Here the attribute "name" is the annotation's name.
    """
    def __init__(self, *, db_expression: BaseExpression, **kwargs):
        super().__init__(**kwargs)
        self._db_expression = db_expression


# ------------------------------------------------------------------------------
# TODO: unit test
class AbstractCellSorter:
    """Abstract base class for QuerySorter.

    A QuerySorter returns the name of the DB-column to use for ordering a Query
    for a given EntityCell.
    """
    # def get_field_name(self, cell: EntityCell) -> str | None:
    #     """Get the name of the column for a given cell.
    #
    #     @param cell: Instance of EntityCell.
    #     @return: A string (name of a DB-column) or None (meaning "no sort").
    #     """
    #     raise NotImplementedError
    def get_sorting_item(self, cell: EntityCell) -> SortingItem | None:
        """Get the sorting item for a given cell.

        @param cell: Instance of EntityCell.
        @return: <None> means "no sorting".
        """
        raise NotImplementedError

    def pretty(self, indent: int = 0) -> str:
        """Get a pretty string to analyze registered items.

        @param indent: Indentation level.
        @return: A string.
        """
        return ' ' * indent + type(self).__name__


class VoidSorter(AbstractCellSorter):
    """Class of sorter which performs no sort."""
    # def get_field_name(self, cell):
    #     return None
    @override
    def get_sorting_item(self, cell):
        return None


class RegularFieldSorter(AbstractCellSorter):
    """Class of sorter for EntityCellRegularFields.
    Not adapted for RelatedField (ForeignKey etc...); see ForeignKeySorterRegistry.
    """
    # def get_field_name(self, cell):
    #     return cell.value
    @override
    def get_sorting_item(self, cell):
        return RegularFieldSortingItem(model=cell.model, name=cell.value)


class EntityForeignKeySorter(AbstractCellSorter):
    """Class of sorter for EntityCellRegularFields which field is a
    ForeignKey to CremeEntity.
    """
    # def get_field_name(self, cell):
    #     return cell.value + '__header_filter_search_field'
    @override
    def get_sorting_item(self, cell):
        return RegularFieldSortingItem(
            model=cell.model, name=f'{cell.value}__header_filter_search_field',
        )


class ForeignKeySorterRegistry(AbstractCellSorter):
    """Class of sorter for EntityCellRegularFields which field is a ForeignKey.
    Sub-sorters can be registered to customise the behaviour for specific
    related models.
    """
    DEFAULT_MODELS = (
        (CremeEntity, EntityForeignKeySorter),
    )

    def __init__(
            self,
            models_to_register: Iterable[
                tuple[type[Model], type[AbstractCellSorter]]
            ] = DEFAULT_MODELS):
        self._sorters: ClassKeyedMap = ClassKeyedMap(default=None)

        for model, sorter_cls in models_to_register:
            self.register(model=model, sorter_cls=sorter_cls)

    # def get_field_name(self, cell):
    #     assert isinstance(cell, EntityCellRegularField)
    #
    #     subfield_model = cell.field_info[-1].remote_field.model
    #     sub_sorter = self._sorters[subfield_model]
    #
    #     if sub_sorter is not None:
    #         field_name = sub_sorter.get_field_name(cell=cell)
    #     else:
    #         subfield_ordering = subfield_model._meta.ordering
    #
    #         if subfield_ordering:
    #             field_name = f'{cell.value}__{subfield_ordering[0]}'
    #         else:
    #             logger.critical(
    #                 'ForeignKeySorter: related field model %s should '
    #                 'have Meta.ordering set (we use "id" as fallback)',
    #                 subfield_model,
    #             )
    #             field_name = cell.value + '_id'
    #
    #     return field_name
    @override
    def get_sorting_item(self, cell):
        assert isinstance(cell, EntityCellRegularField)

        subfield_model = cell.field_info[-1].remote_field.model
        sub_sorter = self._sorters[subfield_model]

        if sub_sorter is None:
            subfield_ordering = subfield_model._meta.ordering

            if subfield_ordering:
                field_name = f'{cell.value}__{subfield_ordering[0]}'
            else:
                logger.critical(
                    'ForeignKeySorter: related field model %s should '
                    'have Meta.ordering set (we use "id" as fallback)',
                    subfield_model,
                )

                # TODO: manage models with PK not named "id"
                field_name = f'{cell.value}_id'

            return RegularFieldSortingItem(model=cell.model, name=field_name)

        return sub_sorter.get_sorting_item(cell=cell)

    @override
    def pretty(self, indent=0):
        indent_str = ' ' * indent
        res = f'{indent_str}{type(self).__name__}:\n{indent_str}  Models:'

        sorters = self._sorters
        if sorters:
            for model, sorter in sorters.items():
                res += '\n{indent}    [{module}.{cls}]:\n{sorter}'.format(
                    indent=indent_str,
                    module=model.__module__,
                    cls=model.__name__,
                    sorter=sorter.pretty(indent=indent + 6),
                )
        else:
            res += f'\n{indent_str}    (empty)'

        return res

    def register(self, *,
                 model: type[Model],
                 sorter_cls: type[AbstractCellSorter],
                 ) -> Self:
        self._sorters[model] = sorter_cls()

        return self

    def sorter(self, model: type[Model]) -> AbstractCellSorter | None:
        return self._sorters[model]


class RegularFieldSorterRegistry(AbstractCellSorter):
    """Class of sorter for all types of EntityCellRegularField.

    Sub-sorters can be registered to customise the behaviour for specific
    model-fields & model-field classes.
    """
    DEFAULT_SORTERS = (
        (models.AutoField,    RegularFieldSorter),

        (models.BooleanField, RegularFieldSorter),

        (models.DecimalField, RegularFieldSorter),
        (models.FloatField,   RegularFieldSorter),
        (models.IntegerField, RegularFieldSorter),

        (models.CharField,    RegularFieldSorter),
        (models.TextField,    RegularFieldSorter),

        (models.DateField,    RegularFieldSorter),
        (models.TimeField,    RegularFieldSorter),

        (models.ForeignKey, ForeignKeySorterRegistry),

        # No sorting
        #  models.ManyToManyField
        #  models.OneToOneField
        (models.CommaSeparatedIntegerField, VoidSorter),
        #  models.FilePathField
        #  models.BinaryField
        #  models.UUIDField
        #  (fields.DurationField, VoidSorter),  TODO ?
        (fields.DatePeriodField, VoidSorter),  # TODO: needs JSONField management in the RDBMS...

        # TODO: what about ?
        # (models.DurationField, ...)
        # (models.IPAddressField, ...)
        # (models.GenericIPAddressField, ...)
        # (models.SlugField, ...)
        # (models.URLField, ...)
    )

    def __init__(
            self,
            to_register: Iterable[
                tuple[type[Field], type[AbstractCellSorter]]
            ] = DEFAULT_SORTERS):
        self._sorters_4_modelfields: dict[Field, AbstractCellSorter] = {}
        self._sorters_4_modelfieldtypes: ClassKeyedMap = ClassKeyedMap(default=None)

        for model_field_cls, sorter_cls in to_register:
            self.register_model_field_type(type=model_field_cls, sorter_cls=sorter_cls)

    @override
    # def get_field_name(self, cell):
    def get_sorting_item(self, cell):
        assert isinstance(cell, EntityCellRegularField)
        field_info = cell.field_info

        if isinstance(field_info[0], models.ManyToManyField):
            return None

        field = field_info[-1]
        sorter = (
            self._sorters_4_modelfields.get(field)
            or self._sorters_4_modelfieldtypes[type(field)]
        )

        # return None if sorter is None else sorter.get_field_name(cell=cell)
        return None if sorter is None else sorter.get_sorting_item(cell=cell)

    @override
    def pretty(self, indent=0):
        indent_str = ' ' * indent
        res = f'{indent_str}{type(self).__name__}:\n{indent_str}  Field types:'

        for field_type, sorter in self._sorters_4_modelfieldtypes.items():
            res += '\n{}    [{}.{}]:\n{}'.format(
                indent_str,
                field_type.__module__,
                field_type.__name__,
                sorter.pretty(indent=indent + 6),
            )

        res += f'\n{indent_str}  Fields:'
        modelfields = self._sorters_4_modelfields
        if modelfields:
            for field, sorter in modelfields.items():
                res += '\n{}    [{}]:\n{}'.format(
                    indent_str,
                    field,
                    sorter.pretty(indent=indent + 6),
                )
        else:
            res += f'\n{indent_str}    (empty)'

        return res

    def register_model_field(self, *,
                             model: type[Model],
                             field_name: str,
                             sorter_cls: type[AbstractCellSorter],
                             ) -> Self:
        field = model._meta.get_field(field_name)
        self._sorters_4_modelfields[field] = sorter_cls()

        # TODO ?
        # if self._enums_4_fields.setdefault(field, enumerator_class) is not enumerator_class:
        #     raise self.RegistrationError(
        #         '_EnumerableRegistry: this field is already registered: {model}.{field}'.format(
        #             model=model.__name__, field=field_name,
        #         )
        #     )

        return self

    def register_model_field_type(self, *,
                                  type: type[Field],
                                  sorter_cls: type[AbstractCellSorter],
                                  ) -> Self:
        self._sorters_4_modelfieldtypes[type] = sorter_cls()

        return self

    def sorter_4_model_field(self, *,
                             model: type[Model],
                             field_name: str) -> AbstractCellSorter | None:
        field = model._meta.get_field(field_name)
        return self._sorters_4_modelfields.get(field)

    def sorter_4_model_field_type(self,
                                  model_field: type[Field],
                                  ) -> AbstractCellSorter | None:
        return self._sorters_4_modelfieldtypes[model_field]


class CustomFieldSorterRegistry(AbstractCellSorter):
    """Class of sorter for all types of EntityCellCustomFields."""
    DEFAULT_SORTABLE_TYPES = (
        CustomField.INT,
        CustomField.FLOAT,
        CustomField.BOOL,
        CustomField.STR,
        # CustomField.TEXT, ??
        # CustomField.URL,  ??
        CustomField.DATETIME,
        CustomField.DATE,

        # NOPE:
        # CustomField.ENUM,
        # CustomField.MULTI_ENUM,
    )

    def __init__(self, to_register: Iterable[int] = DEFAULT_SORTABLE_TYPES):
        self._cfield_type_ids: set[int] = set()
        self.register(*to_register)

    @override
    def get_sorting_item(self, cell):
        assert isinstance(cell, EntityCellCustomField)

        cfield = cell.custom_field

        # NB: because of the implementation of the Custom-Fields (e.g. all the
        #     fields with type INT store their values in the same table), we
        #     cannot just order with something like 'customfieldinteger__value'
        #     (because it could perform a JOIN with several custom values).
        #     We use an annotation + SubQuery to retreive the right custom value to use.
        if cfield.field_type in self._cfield_type_ids:
            return AnnotationSortingItem(
                model=cell.model,
                name=f'customfield-{cfield.id}',
                db_expression=models.Subquery(
                    cfield.value_class.objects.filter(
                        entity=models.OuterRef('pk'), custom_field=cfield,
                    ).values_list('value', flat=True).values('value')[:1],
                ),
            )
        return None

    def register(self, *cfield_type_ids: int) -> Self:
        self._cfield_type_ids.update(cfield_type_ids)

        return self


class FunctionFieldSorterRegistry(AbstractCellSorter):
    """Class of sorter for all types of EntityCellFunctionField.

    By default, it performs no sort, but sub-sorters can be registered to
    customise the behaviour for specific FunctionFields.
    """
    def __init__(self,
                 to_register: Iterable[tuple[FunctionField, type[AbstractCellSorter]]] = (),
                 ):
        self._sorters: dict[str, AbstractCellSorter] = {}

        for ffield, sorter_cls in to_register:
            self.register(ffield=ffield, sorter_cls=sorter_cls)

    @override
    # def get_field_name(self, cell):
    def get_sorting_item(self, cell):
        assert isinstance(cell, EntityCellFunctionField)

        ffield = cell.function_field
        sorter = self._sorters.get(ffield.name)

        if sorter is None:
            sorter_cls = ffield.sorter_class

            if sorter_cls is not None:
                sorter = sorter_cls()

        # return None if sorter is None else sorter.get_field_name(cell=cell)
        return None if sorter is None else sorter.get_sorting_item(cell=cell)

    def register(self, *,
                 ffield: FunctionField,
                 sorter_cls: type[AbstractCellSorter],
                 ) -> Self:
        self._sorters[ffield.name] = sorter_cls()

        return self

    def sorter(self, ffield: FunctionField) -> AbstractCellSorter | None:
        return self._sorters.get(ffield.name)


class CellSorterRegistry(AbstractCellSorter):
    """Class of sorter with registered sub-sorters by kind of EntityCell."""
    DEFAULT_REGISTRIES = (
        (EntityCellRegularField.type_id,  RegularFieldSorterRegistry),
        (EntityCellCustomField.type_id,   CustomFieldSorterRegistry),
        (EntityCellFunctionField.type_id, FunctionFieldSorterRegistry),
        # NB: is ordering by Relations meaning anything (it's like M2M case)?
        #     + beware with mess with JOIN if search at the same time (TODO: use SubQuery?)
        #   (EntityCellRelation.type_id,   ...),
        # NB: not useful because volatile cells cannot be retrieved by HeaderFilter.cells()
        #   (EntityCellVolatile.type_id, ...),
    )

    def __init__(self, to_register=DEFAULT_REGISTRIES):
        self._registries: dict[str, AbstractCellSorter] = {}

        for cell_id, registry_class in to_register:
            self.register(cell_id=cell_id, registry_class=registry_class)

    def __getitem__(self, cell_type_id: str) -> AbstractCellSorter:
        return self._registries[cell_type_id]

    # def get_field_name(self, cell):
    #     try:
    #         field_name = self._registries[cell.type_id].get_field_name(cell)
    #     except KeyError:
    #         field_name = None
    #
    #     return field_name
    @override
    def get_sorting_item(self, cell):
        try:
            item = self._registries[cell.type_id].get_sorting_item(cell)
        except KeyError:
            item = None

        return item

    # TODO: factorise with ListViewSearchFieldRegistry
    def pretty(self, indent=0):
        indent_str = ' ' * indent
        res = f'{indent_str}{type(self).__name__}:'

        def get_alias(cell_id):
            try:
                cell_cls = CELLS_MAP[cell_id]
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

    def register(self, *, cell_id: str, registry_class: type[AbstractCellSorter]) -> Self:
        self._registries[cell_id] = registry_class()

        return self


# ------------------------------------------------------------------------------
class QuerySorter:
    """Builds a QuerySortInfo (see the main method 'get()')."""
    def __init__(self, cell_sorter_registry: CellSorterRegistry | None = None):
        """Constructor.

        @param cell_sorter_registry: Instance of CellSorterRegistry ; by default
               a new one if instantiated.
        """
        self._registry = cell_sorter_registry or CellSorterRegistry()

    # def _get_field_name(self,
    #                     cells_dict: dict[str, EntityCell],
    #                     cell_key: str | None,
    #                     ) -> str | None:
    #     if not cell_key:
    #         return None
    #
    #     cell = cells_dict.get(cell_key)
    #
    #     if cell is None:
    #         logger.warning(
    #             'QuerySorterBuilder -> no available column with key="%s"',
    #             cell_key,
    #         )
    #         return None
    #
    #     return self._registry.get_field_name(cell)
    def _get_sorting_item(self,
                          cells_dict: dict[str, EntityCell],
                          cell_key: str | None,
                          ) -> SortingItem | None:
        if not cell_key:
            return None

        cell = cells_dict.get(cell_key)

        if cell is None:
            logger.warning(
                'QuerySorterBuilder -> no available column with key="%s"',
                cell_key,
            )
            return None

        return self._registry.get_sorting_item(cell)

    @classmethod
    def _default_key_n_order(cls,
                             model: type[Model],
                             ordering: list[str],
                             ) -> tuple[str | None, Order]:
        if not ordering:
            return None, Order()

        ofield = OrderedField(ordering[0])
        cell = EntityCellRegularField.build(model, ofield.field_name)
        assert cell is not None

        return cell.key, ofield.order

    # TODO: factorise with utils.db.get_stable_ordering()?
    # TODO: use model._meta.pk_fields (composite pk)?
    # TODO: what about unique_together ??
    # TODO: move to utils.meta ?
    @staticmethod
    def _get_local_id_field(model: type[Model]) -> Field:
        for field in model._meta.local_concrete_fields:
            if field.unique:
                return field

        raise LookupError('No local unique field found')

    @staticmethod
    def _is_field_unique(model: type[Model], field_name: str) -> bool:
        warnings.warn(
            'QuerySorter._is_field_unique() is deprecated.', DeprecationWarning
        )

        try:
            field = model._meta.get_field(field_name)
        except FieldDoesNotExist:
            return False

        return field.unique

    def get(self,
            model: type[CremeEntity],
            cells: Iterable[EntityCell],
            cell_key: str,
            order: Order | None = None,
            fast_mode: bool = False,
            ) -> QuerySortInfo:
        """Get a QuerySortInfo instance for a model & a main ordering cell,
        using the natural ordering of this model & the DB-indices.

        @param model: CremeEntity subclass.
        @param cells: Sequence of displayed EntityCells (e.g. columns of the list-view) ;
                If the natural ordering fields of the model are not present within the
                cells, they are not used in the result (excepted if it allows to use a
                DB-index).
        @param cell_key: Key of the main (i.e. first) ordering cell (string).
        @param order: <creme_core.utils.meta.Order> instance (or None, meaning "ASC order").
        @param fast_mode: Boolean ; <True> means "There are lots of entities, use
               a faster/simpler ordering".
        @return: A QuerySortInfo instance.
        """
        # if order is None:
        #     order = Order()
        #
        # cells_dict = {c.key: c for c in cells}
        #
        # build_cell = partial(EntityCellRegularField.build, model=model)
        # ordering = [
        #     ofield_str
        #     for ofield_str in model._meta.ordering
        #     if build_cell(name=OrderedField(ofield_str).field_name).key in cells_dict
        # ]
        # sort_field = self._get_field_name(cells_dict, cell_key)
        # final_cell_key: str | None
        #
        # if sort_field:
        #     final_cell_key = cell_key
        #
        #     for ordered_field_str in (sort_field, '-' + sort_field):
        #         if ordered_field_str in ordering:
        #             ordering.remove(ordered_field_str)
        #             ordering.insert(0, sort_field)
        #
        #             if order.desc:
        #                 ordering = [str(OrderedField(o).reversed()) for o in ordering]
        #
        #             break
        #     else:
        #         ordering.insert(0, order.prefix + sort_field)
        # else:
        #     final_cell_key, order = self._default_key_n_order(model, ordering)
        #
        # sort_info = QuerySortInfo(cell_key=final_cell_key, order=order)
        #
        # if sort_field and self._is_field_unique(model, sort_field):
        #     ind_ordering = get_indexed_ordering(model, [*ordering, '*'])
        #
        #     if ind_ordering is not None:
        #         sort_info.field_names = ind_ordering
        #     elif fast_mode:
        #         o_sort_field = order.prefix + sort_field
        #         ind_ordering = get_indexed_ordering(model, [o_sort_field, '*'])
        #         # NB: mypy understands when we use a if/else blocks...
        #         sort_info.field_names = (o_sort_field,) if ind_ordering is None else ind_ordering
        #     else:
        #         sort_info.field_names = tuple(ordering)
        # else:
        #     last_field: str = order.prefix + self._get_local_id_field(model).attname
        #
        #     if ordering:
        #         ind_ordering = get_indexed_ordering(model, [*ordering, '*', last_field])
        #
        #         if ind_ordering is not None:
        #             sort_info.field_names = ind_ordering
        #         elif fast_mode:
        #             first_order = ordering[0]
        #             ind_ordering = get_indexed_ordering(model, [first_order, '*', last_field])
        #
        #             sort_info.field_names = (
        #                 (first_order, last_field) if ind_ordering is None else ind_ordering
        #             )
        #         else:
        #             sort_info.field_names = (*ordering, last_field)
        #     else:
        #         sort_info.field_names = (last_field,)
        #
        # return sort_info
        if order is None:
            order = Order()

        cells_dict = {c.key: c for c in cells}

        build_cell = partial(EntityCellRegularField.build, model=model)
        ordering: list[str] = [
            ofield_str
            for ofield_str in model._meta.ordering
            if build_cell(name=OrderedField(ofield_str).field_name).key in cells_dict
        ]
        sorting_item = self._get_sorting_item(cells_dict, cell_key)
        final_cell_key: str | None

        if sorting_item:
            final_cell_key = cell_key
            sort_key = sorting_item.name

            for ordered_sort_key in (sort_key, f'-{sort_key}'):
                if ordered_sort_key in ordering:
                    ordering.remove(ordered_sort_key)
                    ordering.insert(0, sort_key)

                    if order.desc:
                        ordering = [str(OrderedField(o).reversed()) for o in ordering]

                    break
            else:
                ordering.insert(0, order.prefix + sort_key)
        else:
            final_cell_key, order = self._default_key_n_order(model, ordering)

        sort_info = QuerySortInfo(
            cell_key=final_cell_key, order=order,
            orm_annotations={
                sorting_item.name: sorting_item.db_expression,
            } if (sorting_item and sorting_item.db_expression) else None,
        )

        if sorting_item and sorting_item.is_unique:
            ind_ordering = get_indexed_ordering(model, [*ordering, '*'])

            if ind_ordering is not None:
                sort_info.field_names = ind_ordering
            elif fast_mode:
                o_sort_field = order.prefix + sort_key
                ind_ordering = get_indexed_ordering(model, [o_sort_field, '*'])
                # NB: mypy understands when we use <if/else> blocks...
                sort_info.field_names = (o_sort_field,) if ind_ordering is None else ind_ordering
            else:
                sort_info.field_names = tuple(ordering)
        else:
            # NB: we order by ID (like 'cremeentity_ptr_id' in entity sub-classes)
            #     in order to be sure that successive queries give consistent contents
            #     (if you order by 'name' & there are some duplicated names,
            #     the order by directive can be respected, but the order of the
            #     duplicates in the queries results be different -- so the
            #     paginated contents are not consistent).
            last_field: str = order.prefix + self._get_local_id_field(model).attname

            if ordering:
                ind_ordering = get_indexed_ordering(model, [*ordering, '*', last_field])

                if ind_ordering is not None:
                    sort_info.field_names = ind_ordering
                elif fast_mode:
                    first_order = ordering[0]
                    ind_ordering = get_indexed_ordering(model, [first_order, '*', last_field])

                    sort_info.field_names = (
                        (first_order, last_field) if ind_ordering is None else ind_ordering
                    )
                else:
                    sort_info.field_names = (*ordering, last_field)
            else:
                sort_info.field_names = (last_field,)

        return sort_info

    @property
    def registry(self) -> CellSorterRegistry:
        return self._registry


cell_sorter_registry = CellSorterRegistry()
