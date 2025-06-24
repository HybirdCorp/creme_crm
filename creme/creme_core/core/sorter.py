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

import logging
from collections.abc import Iterable
from functools import partial

from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.db.models import Field, Model

from creme.creme_core.core.entity_cell import (
    CELLS_MAP,
    EntityCell,
    EntityCellFunctionField,
    EntityCellRegularField,
)
from creme.creme_core.core.function_field import FunctionField
from creme.creme_core.models import CremeEntity, fields
from creme.creme_core.utils.collections import ClassKeyedMap
from creme.creme_core.utils.db import get_indexed_ordering
from creme.creme_core.utils.meta import Order, OrderedField

logger = logging.getLogger(__name__)


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

    def __init__(self, cell_key: str | None, order: Order, field_names: tuple[str, ...] = ()):
        self.main_cell_key = cell_key
        self.main_order = order
        self.field_names = field_names

    def __repr__(self):
        return (
            f'<QuerySortInfo('
            f'cell_key={self.main_cell_key!r}, '
            f'order={self.main_order!r}, '
            f'field_names={self.field_names}'
            f')>'
        )


class AbstractCellSorter:
    """Abstract base class for QuerySorter.

    A QuerySorter returns the name of the DB-column to use for ordering a Query
    for a given EntityCell.
    """
    def get_field_name(self, cell: EntityCell) -> str | None:
        """Get the name of the column for a given cell.

        @param cell: Instance of EntityCell.
        @return: A string (name of a DB-column) or None (meaning "no sort").
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
    def get_field_name(self, cell):
        return None


class RegularFieldSorter(AbstractCellSorter):
    """Class of sorter for EntityCellRegularFields.
    Not adapted for RelatedField (ForeignKey etc...) ; see ForeignKeySorterRegistry.
    """
    def get_field_name(self, cell):
        return cell.value


class EntityForeignKeySorter(AbstractCellSorter):
    """Class of sorter for EntityCellRegularFields which field is a
    ForeignKey to CremeEntity.
    """
    def get_field_name(self, cell):
        return cell.value + '__header_filter_search_field'


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

    def get_field_name(self, cell):
        assert isinstance(cell, EntityCellRegularField)

        subfield_model = cell.field_info[-1].remote_field.model
        sub_sorter = self._sorters[subfield_model]

        if sub_sorter is not None:
            field_name = sub_sorter.get_field_name(cell=cell)
        else:
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
                field_name = cell.value + '_id'

        return field_name

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
                 ) -> ForeignKeySorterRegistry:
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

    def get_field_name(self, cell) -> str | None:
        assert isinstance(cell, EntityCellRegularField)
        field_info = cell.field_info

        if isinstance(field_info[0], models.ManyToManyField):
            return None

        field = field_info[-1]
        sorter = (
            self._sorters_4_modelfields.get(field)
            or self._sorters_4_modelfieldtypes[type(field)]
        )

        return None if sorter is None else sorter.get_field_name(cell=cell)

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
                             ):
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
                                  ):
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

    def get_field_name(self, cell) -> str | None:
        assert isinstance(cell, EntityCellFunctionField)

        ffield = cell.function_field
        sorter = self._sorters.get(ffield.name)

        if sorter is None:
            sorter_cls = ffield.sorter_class

            if sorter_cls is not None:
                sorter = sorter_cls()

        return None if sorter is None else sorter.get_field_name(cell=cell)

    def register(self, *, ffield: FunctionField, sorter_cls: type[AbstractCellSorter]):
        self._sorters[ffield.name] = sorter_cls()

        return self

    def sorter(self, ffield: FunctionField) -> AbstractCellSorter | None:
        return self._sorters.get(ffield.name)


class CellSorterRegistry(AbstractCellSorter):
    """Class of sorter with registered sub-sorters by kind of EntityCell."""
    DEFAULT_REGISTRIES = (
        (EntityCellRegularField.type_id,  RegularFieldSorterRegistry),
        (EntityCellFunctionField.type_id, FunctionFieldSorterRegistry),
        # NB: mess with JOIN if search at the same time
        #   (EntityCellCustomField.type_id,   ...),
        #   (EntityCellRelation.type_id,   ...),
        # NB: not useful because volatile cells cannot be retrieved by HeaderFilter.cells()
        #   (EntityCellVolatile.type_id, ...),
    )

    def __init__(self, to_register=DEFAULT_REGISTRIES):
        self._registries = {}

        for cell_id, registry_class in to_register:
            self.register(cell_id=cell_id, registry_class=registry_class)

    def __getitem__(self, cell_type_id: str):
        return self._registries[cell_type_id]

    def get_field_name(self, cell):
        try:
            field_name = self._registries[cell.type_id].get_field_name(cell)
        except KeyError:
            field_name = None

        return field_name

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

    def register(self, *, cell_id, registry_class):
        self._registries[cell_id] = registry_class()

        return self


class QuerySorter:
    """Builds a QuerySortInfo (see the main method 'get()')."""
    def __init__(self, cell_sorter_registry: CellSorterRegistry | None = None):
        """Constructor.

        @param cell_sorter_registry: Instance of CellSorterRegistry ; by default
               a new one if instantiated.
        """
        self._registry = cell_sorter_registry or CellSorterRegistry()

    def _get_field_name(self,
                        cells_dict: dict[str, EntityCell],
                        cell_key: str | None,
                        ) -> str | None:
        if not cell_key:
            return None

        cell = cells_dict.get(cell_key)

        if cell is None:
            logger.warning('QuerySorterBuilder: no such sortable column "%s"', cell_key)
            return None

        return self._registry.get_field_name(cell)

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
        if order is None:
            order = Order()

        cells_dict = {c.key: c for c in cells}

        build_cell = partial(EntityCellRegularField.build, model=model)
        ordering = [
            ofield_str
            for ofield_str in model._meta.ordering
            if build_cell(name=OrderedField(ofield_str).field_name).key in cells_dict
        ]

        # Name of the main model-field used to perform the "ORDER BY" instruction.
        sort_field = self._get_field_name(cells_dict, cell_key)

        final_cell_key: str | None

        if sort_field:
            final_cell_key = cell_key

            for ordered_field_str in (sort_field, '-' + sort_field):
                if ordered_field_str in ordering:
                    ordering.remove(ordered_field_str)
                    ordering.insert(0, sort_field)

                    if order.desc:
                        ordering = [str(OrderedField(o).reversed()) for o in ordering]

                    break
            else:
                ordering.insert(0, order.prefix + sort_field)
        else:
            final_cell_key, order = self._default_key_n_order(model, ordering)

        sort_info = QuerySortInfo(cell_key=final_cell_key, order=order)

        if sort_field and self._is_field_unique(model, sort_field):
            ind_ordering = get_indexed_ordering(model, [*ordering, '*'])

            if ind_ordering is not None:
                sort_info.field_names = ind_ordering
            elif fast_mode:
                o_sort_field = order.prefix + sort_field
                ind_ordering = get_indexed_ordering(model, [o_sort_field, '*'])
                # NB: mypy understands when we use a if/else blocks...
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
