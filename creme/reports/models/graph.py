# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from django.db.models import (PositiveIntegerField, CharField, BooleanField,
        ForeignKey, FieldDoesNotExist)
from django.utils.translation import ugettext_lazy as _, pgettext_lazy, ugettext

from creme.creme_core.models import CremeEntity, RelationType, InstanceBlockConfigItem
#from creme.creme_core.utils.meta import FieldInfo #get_verbose_field_name

from ..constants import RFT_RELATION, RFT_FIELD
from .report import Report


logger = logging.getLogger(__name__)



class ReportGraph(CremeEntity):
    name     = CharField(pgettext_lazy('reports-graphs', u'Name of the graph'), max_length=100)
    report   = ForeignKey(Report)
    abscissa = CharField(_(u'Abscissa axis'), max_length=100)
    ordinate = CharField(_(u'Ordinate axis'), max_length=100)
    type     = PositiveIntegerField(_(u'Type')) #see RGT_*
    days     = PositiveIntegerField(_(u'Days'), blank=True, null=True)
    is_count = BooleanField(_(u'Make a count instead of aggregate?')) #TODO: 'count' function instead ???

    creation_label = _("Add a report's graph")

    _hand = None

    class Meta:
        app_label = 'reports'
        verbose_name = _(u"Report's graph")
        verbose_name_plural = _(u"Reports' graphs")
        ordering = ['name']

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "/reports/graph/%s" % self.id

    #def get_edit_absolute_url(self):
        #return "/reports/graph/edit/%s" % self.id

    def get_related_entity(self):
        return self.report

    def fetch(self, extra_q=None, order='ASC'):
        assert order == 'ASC' or order == 'DESC'
        report = self.report
        entities = report.ct.model_class().objects.filter(is_deleted=False)

        if report.filter is not None:
            entities = report.filter.filter(entities)

        if extra_q is not None:
            entities = entities.filter(extra_q)

        return self.hand.fetch(entities, order)

    @staticmethod
    def get_fetcher_from_instance_block(instance_block_config):
        """Build a GraphFetcher related to this ReportGraph & an InstanceBlockConfigItem.
        @param instance_block_config An instance of InstanceBlockConfigItem.
        @return A GraphFetcher instance.
        """
        from ..core.graph import (GraphFetcher, RegularFieldLinkedGraphFetcher,
                    RelationLinkedGraphFetcher)

        data = instance_block_config.data
        volatile_column = rfield_type = None

        if data:
            try:
                volatile_column, rfield_type = data.split('|', 1)
                rfield_type = int(rfield_type)
            except ValueError as e:
                logger.warn('Instance block: invalid link type "%s" in block "%s" [%s].',
                            data, instance_block_config, e,
                           )

        graph = instance_block_config.entity.get_real_entity()

        #TODO: use a map/registry of GraphFetcher classes
        if rfield_type == RFT_FIELD:
            fetcher = RegularFieldLinkedGraphFetcher(volatile_column, graph)
        elif rfield_type == RFT_RELATION:
            fetcher = RelationLinkedGraphFetcher(volatile_column, graph)
        else:
            fetcher = GraphFetcher(graph)

        return fetcher

    @property
    def hand(self):
        from ..core.graph import RGRAPH_HANDS_MAP #lazy loading

        hand = self._hand

        if hand is None:
            self._hand = hand = RGRAPH_HANDS_MAP[self.type](self)

        return hand

    class InstanceBlockConfigItemError(Exception):
        pass

    def create_instance_block_config_item(self, volatile_field=None, volatile_rtype=None, save=True):
        from ..blocks import ReportGraphBlock
        from ..core.graph import RegularFieldLinkedGraphFetcher

        if volatile_field:
            assert volatile_rtype is None
            error = RegularFieldLinkedGraphFetcher.validate_fieldname(self, volatile_field)

            if error:
                logger.info('ReportGraph.create_instance_block_config_item(): '
                            '%s -> InstanceBlockConfigItem not built.', error
                           )

                return None

            key = '%s|%s' % (volatile_field, RFT_FIELD)
        elif volatile_rtype:
            key = '%s|%s' % (volatile_rtype.id, RFT_RELATION)
        else:
            key = ''

        block_id = InstanceBlockConfigItem.generate_id(ReportGraphBlock, self, key)

        if InstanceBlockConfigItem.objects.filter(block_id=block_id).exists():
            raise self.InstanceBlockConfigItemError(
                        ugettext(u'The instance block for "%s" with these parameters already exists!') % self
                    )

        ibci = InstanceBlockConfigItem(entity=self, block_id=block_id, data=key)

        if save:
            ibci.save()

        return ibci
