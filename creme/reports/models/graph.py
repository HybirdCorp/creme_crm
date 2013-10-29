# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

#import logging

from django.db.models import PositiveIntegerField, CharField, BooleanField, ForeignKey
from django.utils.translation import ugettext_lazy as _, pgettext_lazy, ugettext

from creme.creme_core.models import CremeEntity, InstanceBlockConfigItem
from creme.creme_core.models.header_filter import HFI_RELATION, HFI_FIELD
from creme.creme_core.utils.meta import get_verbose_field_name

from .report import Report


#logger = logging.getLogger(__name__)


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

        entities = report.ct.model_class().objects.all()

        if report.filter is not None:
            entities = report.filter.filter(entities)

        if extra_q is not None:
            entities = entities.filter(extra_q)

        return self.hand.fetch(entities, order)

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
        from creme.reports.blocks import ReportGraphBlock

        if volatile_field: #TODO: unit test
            assert volatile_rtype is None
            verbose = get_verbose_field_name(self.report.ct.model_class(), volatile_field)
            key = u"%s|%s" % (volatile_field, HFI_FIELD)
        elif volatile_rtype:
            verbose = unicode(volatile_rtype)
            key = u"%s|%s" % (volatile_rtype.id, HFI_RELATION)
        else:
            verbose = ugettext(u'None')
            key = ''

        block_id = InstanceBlockConfigItem.generate_id(ReportGraphBlock, self, key)

        if InstanceBlockConfigItem.objects.filter(block_id=block_id).exists():
            raise self.InstanceBlockConfigItemError(
                        ugettext(u'The instance block for %(graph)s with %(column)s already exists !') % {
                                        'graph':  self,
                                        'column': verbose,
                                    }
                    )

        ibci = InstanceBlockConfigItem(entity=self, block_id=block_id, data=key,
                                       verbose=u"%s - %s" % (self, verbose),
                                      )

        if save:
            ibci.save()

        return ibci
