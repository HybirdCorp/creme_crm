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

from django.template import Library
from django.utils.translation import ugettext_lazy as _ #TODO: ugettext instead ?

from creme.creme_core.utils.meta import get_verbose_field_name
from creme.creme_core.models.relation import RelationType

from ..models.graph import RGT_RELATION
from ..report_aggregation_registry import field_aggregation_registry


register = Library()

@register.filter(name="verbose_abscissa")
def get_verbose_abscissa(report_graph, graph_abscissa):
    if report_graph.type == RGT_RELATION:
        try:
            return RelationType.objects.get(pk=graph_abscissa).predicate
        except RelationType.DoesNotExist:
            return u""

    return get_verbose_field_name(report_graph.report.ct.model_class(), graph_abscissa)

@register.filter(name="verbose_ordinate")
def get_verbose_ordinate(report_graph, graph_ordinate):
    if report_graph.is_count:
        return _(u"Count")

    ordinate, sep, aggregate = graph_ordinate.rpartition('__')

    verbose_field_name = get_verbose_field_name(report_graph.report.ct.model_class(), ordinate)
    field_aggregate = field_aggregation_registry.get(aggregate)
    field_aggregate = field_aggregate.title if field_aggregate else u''

    return u"%s - %s" % (verbose_field_name, unicode(field_aggregate))

