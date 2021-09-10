# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

import logging
# import warnings
from typing import TYPE_CHECKING, List, Optional, Tuple, Type

from django.conf import settings
from django.db import models
from django.urls import reverse
# from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.models import (  # RelationType
    CremeEntity,
    InstanceBrickConfigItem,
)

# from ..constants import AGGREGATOR_TYPES, GROUP_TYPES
from .. import constants
from ..core.graph import (
    AbscissaInfo,
    OrdinateInfo,
    abscissa_constraints,
    ordinate_constraints,
)
from ..graph_fetcher_registry import graph_fetcher_registry

if TYPE_CHECKING:
    from ..core.graph import ReportGraphHand  # GraphFetcher

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
        # _('X axis (grouping)'), editable=False, choices=GROUP_TYPES.items(),
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
        # choices=AGGREGATOR_TYPES.items(), default='',
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
    _hand: Optional['ReportGraphHand'] = None

    class Meta:
        abstract = True
        # manager_inheritance_from_future = True
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
    def abscissa_info(self) -> Optional[AbscissaInfo]:
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
    def ordinate_info(self) -> Optional[OrdinateInfo]:
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
              extra_q: Optional[models.Q] = None,
              order: str = 'ASC') -> Tuple[List[str], list]:
        assert order == 'ASC' or order == 'DESC'

        report = self.linked_report
        entities = EntityCredentials.filter(
            user=user,
            queryset=report.ct.model_class().objects.filter(is_deleted=False),
        )

        if report.filter is not None:
            entities = report.filter.filter(entities)

        return self.hand.fetch(entities=entities, order=order, user=user, extra_q=extra_q)

    # @staticmethod
    # def get_fetcher_from_instance_brick(
    #         instance_brick_config: InstanceBrickConfigItem) -> 'GraphFetcher':
    #     """Build a GraphFetcher related to this ReportGraph & an InstanceBrickConfigItem.
    #     @param instance_brick_config: An instance of InstanceBrickConfigItem.
    #     @return A GraphFetcher instance.
    #     """
    #     warnings.warn(
    #         'AbstractReportGraph.get_fetcher_from_instance_brick() is deprecated ; '
    #         'use ReportGraphBrick(...).fetcher instead.',
    #         DeprecationWarning
    #     )
    #
    #     from ..bricks import ReportGraphBrick
    #     return ReportGraphBrick(instance_brick_config).fetcher

    @property
    def hand(self) -> 'ReportGraphHand':
        from ..core.graph import RGRAPH_HANDS_MAP  # Lazy loading

        hand = self._hand

        if hand is None:
            self._hand = hand = RGRAPH_HANDS_MAP[self.abscissa_type](self)

        return hand

    # class InstanceBrickConfigItemError(Exception):
    #     def __init__(self, *args, **kwargs):
    #         super().__init__(*args, **kwargs)
    #         warnings.warn(
    #             'AbstractReportGraph.InstanceBrickConfigItemError is deprecated.',
    #             DeprecationWarning
    #         )

    # def create_instance_brick_config_item(self,
    #                                       volatile_field: Optional[str] = None,
    #                                       volatile_rtype: Optional[RelationType] = None,
    #                                       save: bool = True,
    #                                       ) -> Optional[InstanceBrickConfigItem]:
    #     warnings.warn(
    #         'AbstractReportGraph.create_instance_brick_config_item() is deprecated ; '
    #         'use GraphFetcher.create_brick_config_item() instead.',
    #         DeprecationWarning
    #     )
    #
    #     from ..bricks import ReportGraphBrick
    #     from ..constants import RGF_FK, RGF_NOLINK, RGF_RELATION
    #     from ..core.graph.fetcher import RegularFieldLinkedGraphFetcher
    #
    #     ibci = InstanceBrickConfigItem(
    #         entity=self,
    #         brick_class_id=ReportGraphBrick.id_,
    #     )
    #
    #     if volatile_field:
    #         assert volatile_rtype is None
    #         error = RegularFieldLinkedGraphFetcher.validate_fieldname(self, volatile_field)
    #
    #         if error:
    #             logger.warning(
    #                 'ReportGraph.create_instance_brick_config_item(): '
    #                 '%s -> InstanceBrickConfigItem not built.',
    #                 error,
    #             )
    #
    #             return None
    #
    #         ibci.set_extra_data(key='type',  value=RGF_FK)
    #         ibci.set_extra_data(key='value', value=volatile_field)
    #     elif volatile_rtype:
    #         ibci.set_extra_data(key='type',  value=RGF_RELATION)
    #         ibci.set_extra_data(key='value', value=volatile_rtype.id)
    #     else:
    #         ibci.set_extra_data(key='type', value=RGF_NOLINK)
    #
    #     extra_items = dict(ibci.extra_data_items)
    #
    #     for other_ibci in InstanceBrickConfigItem.objects.filter(
    #         entity=self,
    #         brick_class_id=ReportGraphBrick.id_,
    #     ):
    #         if extra_items == dict(other_ibci.extra_data_items):
    #             raise self.InstanceBrickConfigItemError(
    #                 gettext(
    #                     'The instance block for «{graph}» with these parameters already exists!'
    #                 ).format(graph=self)
    #             )
    #
    #     if save:
    #         ibci.save()
    #
    #     return ibci

    @property
    def model(self) -> Type[CremeEntity]:
        return self.linked_report.ct.model_class()


class ReportGraph(AbstractReportGraph):
    class Meta(AbstractReportGraph.Meta):
        swappable = 'REPORTS_GRAPH_MODEL'
