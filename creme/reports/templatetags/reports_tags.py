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
from django.db.models.fields.related import ForeignKey, ManyToManyField
#from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.utils.meta import get_model_field_info # get_verbose_field_name
#from creme.creme_core.models import CustomField, RelationType
from creme.creme_core.registry import creme_registry

#from ..constants import (RFT_FIELD, RFT_RELATION, RFT_FUNCTION,
        #RFT_CUSTOM, RFT_CALCULATED, RFT_RELATED)
#from ..models.graph import (RGT_RELATION, RGT_CUSTOM_DAY, RGT_CUSTOM_MONTH,
                            #RGT_CUSTOM_YEAR, RGT_CUSTOM_RANGE, RGT_CUSTOM_FK)
#from ..report_aggregation_registry import field_aggregation_registry


register = Library()

#TODO: replace by a method in ReportHand
@register.filter(name="is_field_is_linkable")
def is_linkable(field, ct):
    field_infos = get_model_field_info(ct.model_class(), field.name)
    #registred_models = creme_registry.iter_entity_models()
    registred_models = frozenset(creme_registry.iter_entity_models())

    #TODO: any(...)
    for field_dict in field_infos:
        if isinstance(field_dict.get('field'), (ForeignKey, ManyToManyField)) and \
           field_dict.get('model') in registred_models:
            return True

    return False

@register.inclusion_tag('reports/plot/barchart.json', takes_context=True)
def report_barchart_json(context, rgraph):
    context['rgraph'] = rgraph
    return context

@register.inclusion_tag('reports/plot/small_barchart.json', takes_context=True)
def report_small_barchart_json(context, rgraph):
    context['rgraph'] = rgraph
    return context

@register.inclusion_tag('reports/plot/piechart.json', takes_context=True)
def report_piechart_json(context, rgraph, legend_rows=None):
    context['rgraph'] = rgraph
    context['legend_rows'] = legend_rows
    return context

@register.inclusion_tag('reports/plot/tubechart.json', takes_context=True)
def report_tubechart_json(context, rgraph, legend_rows=1):
    context['rgraph'] = rgraph
    context['legend_rows'] = legend_rows
    return context

#@register.inclusion_tag('reports/templatetags/report_chart.html', takes_context=True)
#def get_report_chart(context, report):
    #context['report'] = report
    #return context

#@register.inclusion_tag('reports/templatetags/report_chart_selectors.html', takes_context=True)
#def get_report_chart_selectors(context):
    #return context

#@register.filter(name="verbose_abscissa")
#def get_verbose_abscissa(report_graph, graph_abscissa):
    #gtype = report_graph.type

    #if gtype == RGT_RELATION:
        #try:
            #return RelationType.objects.get(pk=graph_abscissa).predicate
        #except RelationType.DoesNotExist:
            #return u""

    #if gtype in (RGT_CUSTOM_DAY, RGT_CUSTOM_MONTH, RGT_CUSTOM_YEAR, RGT_CUSTOM_RANGE, RGT_CUSTOM_FK):
        #try:
            #cf = CustomField.objects.get(pk=graph_abscissa)
        #except CustomField.DoesNotExist:
            ##logger.warn('ReportGraph.fetch: CustomField with id="%s" does not exist', ordinate_col)
            #return '??'
        #else:
            #return cf.name

    #return get_verbose_field_name(report_graph.report.ct.model_class(), graph_abscissa)

#@register.filter(name="verbose_ordinate")
#def get_verbose_ordinate(report_graph, graph_ordinate):
    #if report_graph.is_count:
        #return ugettext(u"Count")

    #ordinate, sep, aggregation = graph_ordinate.rpartition('__')

    #if ordinate.isdigit(): #CustomField
        #try:
            #cf = CustomField.objects.get(pk=ordinate)
        #except CustomField.DoesNotExist:
            ##logger.warn('ReportGraph.fetch: CustomField with id="%s" does not exist', ordinate_col)
            #verbose_field_name = '??'
        #else:
            #verbose_field_name = cf.name
    #else: #Regular Field
        #verbose_field_name = get_verbose_field_name(report_graph.report.ct.model_class(), ordinate)

    #field_aggregate = field_aggregation_registry.get(aggregation)
    #aggregate_verbose_name = unicode(field_aggregate.title) if field_aggregate else u''

    #return u"%s - %s" % (verbose_field_name, aggregate_verbose_name)
