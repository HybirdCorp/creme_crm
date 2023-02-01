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

import logging
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.models import CremeEntity, InstanceBrickConfigItem

from .. import constants
from ..core.graph import (
    AbscissaInfo,
    OrdinateInfo,
    abscissa_constraints,
    ordinate_constraints,
)
from ..graph_fetcher_registry import graph_fetcher_registry

if TYPE_CHECKING:
    from ..core.graph import ReportGraphHand

logger = logging.getLogger(__name__)


class AbstractReportGraph(CremeEntity):
    Group = constants.AbscissaGroup
    Aggregator = constants.OrdinateAggregator

    name = models.CharField(
        pgettext_lazy('reports-graphs', 'Name of the graph'), max_length=100,
    )

    linked_report = models.ForeignKey(
        settings.REPORTS_REPORT_MODEL, editable=False, on_delete=models.CASCADE,
    )

    # TODO: string IDs instead of integer ?
    abscissa_type = models.PositiveIntegerField(
        _('X axis (grouping)'), editable=False, choices=Group.choices,
    )
    abscissa_cell_value = models.CharField(
        _('X axis (field)'), max_length=100, editable=False,
    )
    abscissa_parameter = models.TextField(
        _('X axis parameter'), null=True, editable=False,
    )

    ordinate_type = models.CharField(
        _('Y axis (type)'), max_length=100, editable=False,
        choices=Aggregator.choices, default='',
    )
    ordinate_cell_key = models.CharField(
        _('Y axis (field)'), max_length=100, editable=False, default='',
    )

    chart = models.CharField(_('Chart type'), max_length=100, null=True)
    asc   = models.BooleanField('ASC order', default=True, editable=False)  # TODO: not viewable ?

    creation_label = _("Create a report's graph")
    save_label     = pgettext_lazy('reports-graphs', 'Save the graph')

    abscissa_constraints = abscissa_constraints
    ordinate_constraints = ordinate_constraints
    fetcher_registry = graph_fetcher_registry
    _hand: ReportGraphHand | None = None

    class Meta:
        abstract = True
        app_label = 'reports'
        verbose_name = _("Report's graph")
        verbose_name_plural = _("Reports' graphs")
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('reports__view_graph', args=(self.id,))

    def get_related_entity(self):
        return self.linked_report

    def delete(self, *args, **kwargs):
        # NB: we call InstanceBrickConfigItem.delete() explicitly to delete
        #     related BrickDetailviewLocation/BrickHomeLocation/... instances
        for ibci in InstanceBrickConfigItem.objects.filter(entity=self.id):
            ibci.delete()

        super().delete(*args, **kwargs)

    @property
    def abscissa_info(self) -> AbscissaInfo | None:
        report = self.linked_report
        assert report is not None

        model = report.ct.model_class()
        abscissa_constraint = self.abscissa_constraints.get_constraint_by_rgraph_type(
            model=model,
            rgraph_type=self.abscissa_type,
        )
        if not abscissa_constraint:
            logger.warning(
                'AbstractReportGraph.abscissa_info: '
                'invalid abscissa info (model=<%s> rgraph_type=%s)',
                model, self.abscissa_type,
            )
            return None

        return AbscissaInfo(
            cell=abscissa_constraint.cell_class.build(
                model,
                self.abscissa_cell_value,
            ),
            graph_type=self.abscissa_type,
            parameter=self.abscissa_parameter,
        )

    @abscissa_info.setter
    def abscissa_info(self, abs_info: AbscissaInfo):
        assert abs_info.cell is not None

        self.abscissa_cell_value = abs_info.cell.value
        self.abscissa_type = abs_info.graph_type
        self.abscissa_parameter = abs_info.parameter

    @property
    def ordinate_info(self) -> OrdinateInfo | None:
        report = self.linked_report
        assert report is not None

        aggr_id = self.ordinate_type
        model = report.ct.model_class()
        ordinate_constraint = self.ordinate_constraints.get_constraint_by_aggr_id(
            model=model,
            aggr_id=aggr_id,
        )
        if not ordinate_constraint:
            logger.warning(
                'AbstractReportGraph.ordinate_info: invalid ordinate info (model=<%s> aggr_id=%s)',
                model, aggr_id,
            )
            return None

        return OrdinateInfo(
            aggr_id=aggr_id,
            cell=ordinate_constraint.get_cell(self.ordinate_cell_key, check=False),
        )

    @ordinate_info.setter
    def ordinate_info(self, ord_info: OrdinateInfo):
        self.ordinate_type = ord_info.aggr_id

        cell = ord_info.cell
        self.ordinate_cell_key = cell.key if cell else ''

    # TODO: use creme_core.utils.meta.Order
    def fetch(self,
              user,
              extra_q: models.Q | None = None,
              order: str = 'ASC',
              ) -> tuple[list[str], list]:
        assert order == 'ASC' or order == 'DESC'

        report = self.linked_report
        entities = EntityCredentials.filter(
            user=user,
            queryset=report.ct.get_all_objects_for_this_type(is_deleted=False),
        )

        if report.filter is not None:
            entities = report.filter.filter(entities)

        return self.hand.fetch(entities=entities, order=order, user=user, extra_q=extra_q)

    @property
    def hand(self) -> ReportGraphHand:
        from ..core.graph import RGRAPH_HANDS_MAP  # Lazy loading

        hand = self._hand

        if hand is None:
            self._hand = hand = RGRAPH_HANDS_MAP[self.abscissa_type](self)

        return hand

    @property
    def model(self) -> type[CremeEntity]:
        return self.linked_report.ct.model_class()

    def verbose_abscissa(self):
        output = self.hand.verbose_abscissa

        if self.abscissa_type:
            output += f' - {self.hand.verbose_name}'

            if self.abscissa_parameter:
                output += f' {self.abscissa_parameter}'

        return output

    def verbose_ordinate(self):
        aggregator = self.hand.ordinate

        if aggregator.cell:
            return f'{aggregator.cell} - {aggregator.verbose_name}'

        return aggregator.verbose_name


class ReportGraph(AbstractReportGraph):
    class Meta(AbstractReportGraph.Meta):
        swappable = 'REPORTS_GRAPH_MODEL'
