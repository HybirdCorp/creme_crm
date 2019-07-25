# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

from django.conf import settings
from django.db.models import PositiveIntegerField, CharField, BooleanField, ForeignKey, CASCADE
from django.urls import reverse
from django.utils.translation import gettext_lazy as _, pgettext_lazy, gettext

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.models import CremeEntity, InstanceBrickConfigItem

from ..constants import RFT_RELATION, RFT_FIELD, GROUP_TYPES

logger = logging.getLogger(__name__)


class AbstractReportGraph(CremeEntity):
    name     = CharField(pgettext_lazy('reports-graphs', 'Name of the graph'), max_length=100)
    linked_report = ForeignKey(settings.REPORTS_REPORT_MODEL, editable=False, on_delete=CASCADE)
    abscissa = CharField(_('X axis'), max_length=100, editable=False)
    ordinate = CharField(_('Y axis'), max_length=100, editable=False)
    type     = PositiveIntegerField(_('Grouping'), editable=False, choices=GROUP_TYPES.items())
    days     = PositiveIntegerField(_('Days'), blank=True, null=True)
    is_count = BooleanField(_('Make a count instead of aggregate?'), default=False)  # TODO: 'count' function instead ?
    chart    = CharField(_('Chart type'), max_length=100, null=True)
    asc      = BooleanField('ASC order', default=True, editable=False)  # TODO: not viewable ?

    creation_label = _("Create a report's graph")
    save_label     = pgettext_lazy('reports-graphs', 'Save the graph')

    _hand = None

    class Meta:
        abstract = True
        manager_inheritance_from_future = True
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

    # TODO: use creme_core.utils.meta.Order
    def fetch(self, user, extra_q=None, order='ASC'):
        assert order == 'ASC' or order == 'DESC'

        report = self.linked_report
        entities = EntityCredentials.filter(
            user=user,
            queryset=report.ct.model_class().objects.filter(is_deleted=False),
        )

        if report.filter is not None:
            entities = report.filter.filter(entities)

        if extra_q is not None:
            entities = entities.filter(extra_q)

        return self.hand.fetch(entities=entities, order=order, user=user)

    # @classmethod
    # def get_fetcher_from_instance_block(cls, instance_block_config):
    #     warnings.warn('AbstractReportGraph.get_fetcher_from_instance_block() is deprecated ; '
    #                   'use get_fetcher_from_instance_brick() instead.',
    #                   DeprecationWarning
    #                  )
    #
    #     return cls.get_fetcher_from_instance_brick(instance_block_config)

    @staticmethod
    def get_fetcher_from_instance_brick(instance_brick_config):
        """Build a GraphFetcher related to this ReportGraph & an InstanceBrickConfigItem.
        @param instance_brick_config: An instance of InstanceBrickConfigItem.
        @return A GraphFetcher instance.
        """
        from ..core import graph as core_graph

        data = instance_brick_config.data
        volatile_column = rfield_type = None

        if data:
            try:
                volatile_column, rfield_type = data.split('|', 1)
                rfield_type = int(rfield_type)
            except ValueError as e:
                logger.warning('Instance block: invalid link type "%s" in block "%s" [%s].',
                               # data, instance_block_config, e,
                               data, instance_brick_config, e,
                              )

        graph = instance_brick_config.entity.get_real_entity()

        # TODO: use a map/registry of GraphFetcher classes
        if rfield_type == RFT_FIELD:
            fetcher = core_graph.RegularFieldLinkedGraphFetcher(volatile_column, graph)
        elif rfield_type == RFT_RELATION:
            fetcher = core_graph.RelationLinkedGraphFetcher(volatile_column, graph)
        else:
            fetcher = core_graph.GraphFetcher(graph)

        return fetcher

    @property
    def hand(self):
        from ..core.graph import RGRAPH_HANDS_MAP  # Lazy loading

        hand = self._hand

        if hand is None:
            self._hand = hand = RGRAPH_HANDS_MAP[self.type](self)

        return hand

    class InstanceBrickConfigItemError(Exception):
        pass

    # class InstanceBlockConfigItemError(Exception):
    #     def __init__(self, *args, **kwarg):
    #         warnings.warn('AbstractReportGraph.InstanceBlockConfigItemError is deprecated ; '
    #                       'use InstanceBrickConfigItemError instead.',
    #                       DeprecationWarning
    #                      )
    #
    #         super().__init__(*args, **kwarg)

    # def create_instance_block_config_item(self, *args, **kwargs):
    #     warnings.warn('AbstractReportGraph.create_instance_block_config_item() is deprecated ; '
    #                   'use create_instance_block_config_item() instead.',
    #                   DeprecationWarning
    #                  )
    #
    #     try:
    #         return self.create_instance_brick_config_item(*args, **kwargs)
    #     except self.InstanceBrickConfigItemError as e:
    #         raise self.InstanceBlockConfigItemError(e.args[0])

    def create_instance_brick_config_item(self, volatile_field=None, volatile_rtype=None, save=True):
        from ..bricks import ReportGraphBrick
        from ..core.graph import RegularFieldLinkedGraphFetcher

        if volatile_field:
            assert volatile_rtype is None
            error = RegularFieldLinkedGraphFetcher.validate_fieldname(self, volatile_field)

            if error:
                logger.info('ReportGraph.create_instance_brick_config_item(): '
                            '%s -> InstanceBrickConfigItem not built.', error
                           )

                return None

            key = '{}|{}'.format(volatile_field, RFT_FIELD)
        elif volatile_rtype:
            key = '{}|{}'.format(volatile_rtype.id, RFT_RELATION)
        else:
            key = ''

        brick_id = InstanceBrickConfigItem.generate_id(ReportGraphBrick, self, key)

        if InstanceBrickConfigItem.objects.filter(brick_id=brick_id).exists():
            raise self.InstanceBrickConfigItemError(
                gettext('The instance block for «{graph}» with these parameters already exists!').format(graph=self)
            )

        ibci = InstanceBrickConfigItem(entity=self, brick_id=brick_id, data=key)

        if save:
            ibci.save()

        return ibci

    @property
    def model(self):
        return self.linked_report.ct.model_class()


class ReportGraph(AbstractReportGraph):
    class Meta(AbstractReportGraph.Meta):
        swappable = 'REPORTS_GRAPH_MODEL'
