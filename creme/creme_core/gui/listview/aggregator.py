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

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import DefaultDict, Iterable, Iterator

from django.db.models import aggregates, fields
from django.utils.formats import number_format
from django.utils.translation import gettext as _

from creme.creme_core.core.entity_cell import (
    EntityCell,
    EntityCellRegularField,
)
from creme.creme_core.models import CremeEntity
from creme.creme_core.utils.meta import FieldInfo


@dataclass(frozen=True, kw_only=True)
class AggregationResult:
    """Contains a numeric value computed by a SQL aggregation (& a label)."""
    value: int | float | Decimal
    label: str

    def render(self) -> str:
        """Returns a human-friendly string."""
        value = self.value
        if isinstance(value, Decimal):
            value = value.normalize()  # Trailing "0" with sqlite
        elif isinstance(value, float):  # TODO: test
            value = Decimal(str(value))

        return _('{aggregation_label}: {aggregation_value}').format(
            aggregation_label=self.label,
            aggregation_value=number_format(value, force_grouping=True),
        )


@dataclass(frozen=True, kw_only=True)
class _ListViewAggregator:
    """Contains the information to build an aggregation query & display the result."""
    field: str  # Field name
    label: str  # Used to build the related AggregationResult
    function: type[aggregates.Aggregate]  # See _ModelAggregatorsRegistry.FUNCTIONS

    @property
    def as_args(self) -> tuple[str, aggregates.Aggregate]:
        """Argument which can be passed to <QuerySet.aggregate()>."""
        func = self.function
        return f'{self.field}/{func.name}', func(self.field)


class _ModelAggregatorsRegistry:
    """Contains the _ListViewAggregator related to a CremeEntity model."""
    # Available aggregation functions
    FUNCTIONS = {
        f.name: f
        for f in (aggregates.Min, aggregates.Max, aggregates.Sum, aggregates.Avg)
    }

    _aggregators: DefaultDict[
        str,  # Field name
        dict[
            str,  # Function name
            _ListViewAggregator
        ]
    ]
    _model: type[CremeEntity]

    def __init__(self, model: type[CremeEntity]):
        self._model = model
        self._aggregators = defaultdict(dict)

    def __str__(self):
        return '_ModelAggregatorsRegistry:\n' + '\n'.join(
            f' - {field_name}: {aggregators}'
            for field_name, aggregators in self._aggregators.items()
        )

    @property
    def model(self) -> type[CremeEntity]:
        return self._model

    def add_aggregator(self, *,
                       field: str,
                       label: str,
                       function: str,
                       ) -> _ModelAggregatorsRegistry:
        """Add an aggregator to the related model.
        @param field: Field name.
               Notice that it can be a "deep" field (i.e. "a_fk__a_field").
        @param label: Used to display the result (see <AggregationResult>).
        @param function: Function name.
               Possible values: "Sum", "Avg", "Max", "Min".
        """
        # NB: can raise FieldDoesNotExist
        field_info = FieldInfo(self._model, field)

        # TODO: test
        if len(field_info) > 2:
            raise ValueError(f'The field chain is too long: {field}')

        if not isinstance(
            field_info[-1],
            (fields.IntegerField, fields.DecimalField, fields.FloatField)
        ):
            raise ValueError(f'This field is not a numeric field: {field}')

        # TODO: case insensitive?
        function_obj = self.FUNCTIONS.get(function)
        if function_obj is None:
            raise ValueError(f'This function is unknown: {function}')

        self._aggregators[field][function] = _ListViewAggregator(
            field=field, label=label, function=function_obj,
        )

        return self

    def remove_aggregator(self, *,
                          field: str,
                          function: str,
                          ) -> _ModelAggregatorsRegistry:
        """Remove a registered aggregator.
        @param field: Field name.
        @param function: Function name.
        @return Self to chain calls.
        """
        try:
            del self._aggregators[field][function]
        except KeyError as e:
            raise ValueError(
                f'No aggregator "{function}" registered for '
                f'the field <{self._model.__name__}.{field}>'
            ) from e

        return self

    def aggregators(self, field: str) -> Iterator[_ListViewAggregator]:
        """All the aggregators related to a field."""
        yield from self._aggregators[field].values()


class ListViewAggregatorRegistry:
    """Registry for aggregator used by the list-views for CremeEntities.
    A field of a model with an aggregator will display additional information
    like the sum of the values for this field for all concerned entities.

    Example:
        registry = ListViewAggregatorRegistry()
        registry.model(Organisation).add_aggregator(
            field='capital', label='Average', function='Avg',
        )
        registry.model(Invoice).add_aggregator(
            field='total_vat', label='Sum', function='Sum',
        ).add_aggregator(
            field='total_vat', label='Max', function='Max',
        )

    Hint: you'll probably use <CremeAppConfig.register_aggregators()>.
    """
    _model_registries: dict[type[CremeEntity], _ModelAggregatorsRegistry]

    def __init__(self):
        self._model_registries = {}

    @property
    def models(self) -> Iterator[type[CremeEntity]]:
        """All models of CremeEntity with aggregators."""
        yield from self._model_registries.keys()

    def aggregators(self, *,
                    model: type[CremeEntity],
                    field: str,
                    ) -> Iterator[_ListViewAggregator]:
        """Get the aggregators registered for the field a model.
        @param model: Concerned entity model.
        @param field: Field name.
        @return Yielded aggregators.
        """
        sub_registry = self._model_registries.get(model)
        if sub_registry is not None:
            yield from sub_registry.aggregators(field=field)

    def model(self, model: type[CremeEntity]) -> _ModelAggregatorsRegistry:
        """Get the sub-registry containing the aggregators for a given model.
        Useful to register & unregister aggregators by chaining with:
         - add_aggregator()
         - remove_aggregator()
        """
        if not issubclass(model, CremeEntity):
            raise ValueError(f'<{model.__name__}> is not a CremeEntity sub-class.')

        model_registries = self._model_registries
        sub_registry = model_registries.get(model)
        if sub_registry is None:
            model_registries[model] = sub_registry = _ModelAggregatorsRegistry(model=model)

        return sub_registry

    def clear_model(self, model: type[CremeEntity]) -> None:
        """Remove the sub-registry related to a madel (& so all related aggregators)."""
        del self._model_registries[model]

    def aggregation_for_cells(self, *,
                              queryset,
                              cells: Iterable[EntityCell],
                              ) -> DefaultDict[str, list[AggregationResult]]:
        """Compute aggregation results.
        @param queryset: Queryset on a CremeEntity subclass. Results will be
               computed with its content.
        @param cells: EntityCells which will be used to know which aggregation to
               perform (i.e. fields which are registered AND referenced by a cell).
        @return A dictionary containing the results per cell keys.
        """
        result = defaultdict(list)
        model = queryset.model
        sub_registry = self.model(model)

        aggregate_kwargs = {}  # Arguments for QuerySet.aggregate()
        aggregations_info = {}  # Key: name of the aggregation; Value (label cell's key)
        for cell in cells:
            if cell.model != model:
                raise ValueError(
                    f'The cell "{cell.key}" is not related to the model <{model.__name__}>'
                )

            if isinstance(cell, EntityCellRegularField):  # TODO: test
                for agg in sub_registry.aggregators(cell.value):
                    agg_name, agg_function = agg.as_args
                    aggregate_kwargs[agg_name] = agg_function
                    aggregations_info[agg_name] = (agg.label, cell.key)

        if aggregate_kwargs:
            for agg_name, agg_value in queryset.aggregate(**aggregate_kwargs).items():
                if agg_value is not None:
                    agg_label, cell_key = aggregations_info[agg_name]
                    result[cell_key].append(
                        AggregationResult(value=agg_value, label=agg_label)
                    )

        return result


aggregator_registry = ListViewAggregatorRegistry()
