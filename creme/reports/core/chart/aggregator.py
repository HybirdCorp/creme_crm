################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2025  Hybird
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
from typing import TYPE_CHECKING

from django.db.models import Q, QuerySet, aggregates
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.entity_cell import (
    EntityCell,
    EntityCellCustomField,
    EntityCellRegularField,
)
from creme.creme_core.models import FieldsConfig
from creme.reports.constants import OrdinateAggregator

if TYPE_CHECKING:
    from creme.reports.models import ReportChart

logger = logging.getLogger(__name__)


class ReportChartAggregator:
    aggr_id: str = ''  # Set by ReportChartAggregatorRegistry decorator

    def __init__(self, *,
                 cell: EntityCell | None = None,
                 error: str | None = None,
                 ):
        self._cell = cell
        self._error: str | None = error

    def annotate(self):
        raise NotImplementedError

    # TODO: improve annotate() API instead?
    @property
    def annotate_extra_q(self):
        return Q()

    def aggregate(self, entities: QuerySet):
        return 0

    @property
    def cell(self) -> EntityCell | None:
        return self._cell

    @property
    def error(self) -> str | None:
        return self._error

    @property
    def verbose_name(self) -> str:
        try:
            return OrdinateAggregator(self.aggr_id).label
        except ValueError:
            return '??'


class ReportChartAggregatorRegistry:
    def __init__(self) -> None:
        self._aggregator_classes: dict[str, type[ReportChartAggregator]] = {}

    def __call__(self, aggr_id: str):
        assert aggr_id not in self._aggregator_classes, 'ID collision'

        def _aux(cls: type[ReportChartAggregator]):
            self._aggregator_classes[aggr_id] = cls
            cls.aggr_id = aggr_id
            return cls

        return _aux

    def __getitem__(self, chart: ReportChart) -> ReportChartAggregator:
        agg_cls = self._aggregator_classes.get(chart.ordinate_type)
        if agg_cls is None:
            logger.warning(
                'ReportChartAggregatorRegistry: the aggregation function <%s> is invalid',
                chart.ordinate_type,
            )
            return ReportChartAggregator(
                cell=None,
                error=_('the aggregation function is invalid.'),
            )

        ord_info = chart.ordinate_info
        if ord_info is None:
            logger.warning(
                'ReportChartAggregatorRegistry: the aggregated field <%s> has a bad type',
                chart.ordinate_cell_key,
            )
            return ReportChartAggregator(
                cell=None,
                error='the aggregated field has a bad type.',
            )

        try:
            return agg_cls(cell=ord_info.cell)
        except ValueError as e:
            logger.warning('ReportChartAggregatorRegistry: %s', e)
            return ReportChartAggregator(
                cell=None,
                error=str(e),
            )


AGGREGATORS_MAP = ReportChartAggregatorRegistry()


@AGGREGATORS_MAP(OrdinateAggregator.COUNT)
class ChartCount(ReportChartAggregator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self._cell is not None:
            raise ValueError(f'{type(self).__name__} does not work with a cell.')

    def annotate(self):
        # TMP: meh, we could model count as an aggregation
        #     (caveat: count is technically *not* aggregating a field here,
        #     whereas our aggregation operators do)
        return aggregates.Count('pk')  # Is there a way to count(*) ?

    def aggregate(self, entities):
        return entities.count()


class _ChartFieldAggregation(ReportChartAggregator):
    aggregate_cls = aggregates.Aggregate

    _aggregate: aggregates.Aggregate

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cell = self._cell
        self._extra_q = Q()

        if cell is None:
            raise ValueError(_('the field does not exist any more.'))

        if isinstance(cell, EntityCellRegularField):
            finfo = cell.field_info

            if FieldsConfig.objects.get_for_model(cell.model).is_field_hidden(finfo[-1]):
                self._error = _('this field should be hidden.')

            self._aggregate = self.aggregate_cls(finfo[0].name)
        elif isinstance(cell, EntityCellCustomField):
            cfield = cell.custom_field
            if cfield.is_deleted:
                self._error = _('this custom field is deleted.')

            related_name = cfield.value_class.get_related_name()
            self._extra_q = Q(**{f'{related_name}__custom_field': cfield.id})
            self._aggregate = self.aggregate_cls(f'{related_name}__value')
        else:  # Should not happen (cell constraint used before to retrieve the cell)
            raise ValueError(f'_ChartFieldAggregation: invalid type of cell <{type(cell)}>')

    def annotate(self):
        return self._aggregate

    @ReportChartAggregator.annotate_extra_q.getter
    def annotate_extra_q(self):
        return self._extra_q

    def aggregate(self, entities):
        return entities.aggregate(
            rga_value_agg=self._aggregate,
        ).get('rga_value_agg') or 0


@AGGREGATORS_MAP(OrdinateAggregator.AVG)
class ChartAverage(_ChartFieldAggregation):
    aggregate_cls = aggregates.Avg


@AGGREGATORS_MAP(OrdinateAggregator.MAX)
class ChartMax(_ChartFieldAggregation):
    aggregate_cls = aggregates.Max


@AGGREGATORS_MAP(OrdinateAggregator.MIN)
class ChartMin(_ChartFieldAggregation):
    aggregate_cls = aggregates.Min


@AGGREGATORS_MAP(OrdinateAggregator.SUM)
class ChartSum(_ChartFieldAggregation):
    aggregate_cls = aggregates.Sum
