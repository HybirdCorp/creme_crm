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
from typing import TYPE_CHECKING
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

import creme.creme_core.models.fields as core_fields
from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.models import (
    CremeEntity,
    CremeModel,
    InstanceBrickConfigItem,
)

from .. import constants
from ..core.chart import (
    AbscissaInfo,
    OrdinateInfo,
    abscissa_constraints,
    chart_fetcher_registry,
    ordinate_constraints,
)

if TYPE_CHECKING:
    from ..core.chart import ReportChartHand

logger = logging.getLogger(__name__)


# NB: some <viewable=False> to avoid useless historisation
class ReportChart(CremeModel):
    Group = constants.AbscissaGroup
    Aggregator = constants.OrdinateAggregator

    user = models.ForeignKey(
        get_user_model(), editable=False,
        null=True, default=None, on_delete=models.SET_NULL,
    ).set_tags(clonable=False)
    created = core_fields.CreationDateTimeField().set_tags(viewable=False, clonable=False)
    modified = core_fields.ModificationDateTimeField().set_tags(viewable=False, clonable=False)

    uuid = models.UUIDField(
        unique=True, editable=False, default=uuid4,
    ).set_tags(viewable=False, clonable=False)
    name = models.CharField(_('Name of the chart'), max_length=100)

    linked_report = models.ForeignKey(
        settings.REPORTS_REPORT_MODEL, editable=False, on_delete=models.CASCADE,
        related_name='charts',
    )

    # Not used in vanilla but migrated from ReportGraph
    description = models.TextField(_('Description'), blank=True)

    # TODO: string IDs instead of integer ?
    abscissa_type = models.PositiveIntegerField(
        _('X axis (grouping)'), editable=False, choices=Group,
    )
    abscissa_cell_value = models.CharField(
        _('X axis (field)'), max_length=100, editable=False,
    )
    abscissa_parameter = models.TextField(
        _('X axis parameter'), null=True, editable=False,
    )

    ordinate_type = models.CharField(
        _('Y axis (type)'), max_length=100, editable=False,
        choices=Aggregator, default='',
    )
    ordinate_cell_key = models.CharField(
        _('Y axis (field)'), max_length=100, editable=False, default='',
    )

    plot_name = models.CharField(
        _('Plot type'), max_length=100, null=True,
    ).set_tags(viewable=False)
    asc = models.BooleanField(
        'ASC order', default=True, editable=False,
    ).set_tags(viewable=False)

    # Can be used by third party code to store the data they want,
    # without having to modify the code.
    # TODO: clonable=False?
    extra_data = models.JSONField(editable=False, default=dict).set_tags(viewable=False)

    creation_label = _('Create a report chart')
    save_label     = _('Save the chart')

    abscissa_constraints = abscissa_constraints
    ordinate_constraints = ordinate_constraints
    fetcher_registry = chart_fetcher_registry
    _hand: ReportChartHand | None = None

    class Meta:
        app_label = 'reports'
        verbose_name = _('Report chart')
        verbose_name_plural = _('Report charts')
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('reports__view_chart', args=(self.id,))

    def get_delete_absolute_url(self):
        return reverse('reports__delete_chart', args=(self.id,))

    def get_related_entity(self):
        return self.linked_report

    def delete(self, *args, **kwargs):
        from creme.reports.bricks import ReportChartInstanceBrick

        # NB: we call InstanceBrickConfigItem.delete() explicitly to delete
        #     related BrickDetailviewLocation/BrickHomeLocation/... instances
        for ibci in InstanceBrickConfigItem.objects.filter(
            entity=self.linked_report_id,
            **{f'json_extra_data__{ReportChartInstanceBrick.chart_key}': str(self.uuid)},
        ):
            ibci.delete()

        super().delete(*args, **kwargs)

    @property
    def abscissa_info(self) -> AbscissaInfo | None:
        report = self.linked_report
        assert report is not None

        model = report.ct.model_class()
        abscissa_constraint = self.abscissa_constraints.get_constraint_by_chart_type(
            model=model, chart_type=self.abscissa_type,
        )
        if not abscissa_constraint:
            logger.warning(
                'ReportChart.abscissa_info: '
                'invalid abscissa info (model=<%s> chart_type=%s)',
                model, self.abscissa_type,
            )
            return None

        return AbscissaInfo(
            cell=abscissa_constraint.cell_class.build(
                model,
                self.abscissa_cell_value,
            ),
            chart_type=self.abscissa_type,
            parameter=self.abscissa_parameter,
        )

    @abscissa_info.setter
    def abscissa_info(self, abs_info: AbscissaInfo):
        assert abs_info.cell is not None

        self.abscissa_cell_value = abs_info.cell.portable_value
        self.abscissa_type = abs_info.chart_type
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
                'ReportChart.ordinate_info: invalid ordinate info (model=<%s> aggr_id=%s)',
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
        self.ordinate_cell_key = cell.portable_key if cell else ''

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

    def fetch_colormap(self, user):
        return self.hand.fetch_colormap(user=user)

    @property
    def hand(self) -> ReportChartHand:
        from ..core.chart import CHART_HANDS_MAP  # Lazy loading

        hand = self._hand

        if hand is None:
            self._hand = hand = CHART_HANDS_MAP[self.abscissa_type](self)

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
