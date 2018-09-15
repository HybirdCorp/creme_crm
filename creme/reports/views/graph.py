# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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
import warnings

from django.db.models import FieldDoesNotExist, DateField, DateTimeField, ForeignKey
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core import utils
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views import generic
from creme.creme_core.models import CremeEntity, InstanceBrickConfigItem, RelationType, CustomField

from .. import get_rgraph_model
from ..constants import (RGT_CUSTOM_DAY, RGT_CUSTOM_MONTH, RGT_CUSTOM_YEAR, RGT_CUSTOM_RANGE,
        RGT_CUSTOM_FK, RGT_RELATION, RGT_DAY, RGT_MONTH, RGT_YEAR, RGT_RANGE, RGT_FK)
from ..core.graph import RGRAPH_HANDS_MAP
from ..forms.graph import ReportGraphForm
from ..report_chart_registry import report_chart_registry


logger = logging.getLogger(__name__)
ReportGraph = get_rgraph_model()

# Function views --------------------------------------------------------------


def abstract_add_rgraph(request, report_id, form=ReportGraphForm,
                        title=_(u'Create a graph for «%s»'),
                        submit_label=ReportGraph.save_label,
                       ):
    return generic.add_to_entity(request, report_id, form, title, submit_label=submit_label)


def abstract_edit_rgraph(request, graph_id, form=ReportGraphForm,
                         title=_(u'Edit a graph for «%s»'),
                        ):
    return generic.edit_related_to_entity(request, graph_id, ReportGraph, form, title)


def abstract_view_rgraph(request, graph_id, template='reports/view_graph.html'):
    warnings.warn('reports.views.graph.abstract_view_rgraph() is deprecated ; '
                  'use the class-based view ReportGraphDetail instead.',
                  DeprecationWarning
                 )
    return generic.view_entity(request, graph_id, ReportGraph,
                               template=template,
                               extra_template_dict={'report_charts': report_chart_registry},
                              )


@login_required
@permission_required('reports')
def add(request, report_id):
    return abstract_add_rgraph(request, report_id)


@login_required
@permission_required('reports')
def edit(request, graph_id):
    return abstract_edit_rgraph(request, graph_id)


@login_required
@permission_required('reports')
def detailview(request, graph_id):
    warnings.warn('reports.views.graph.detailview() is deprecated.', DeprecationWarning)
    return abstract_view_rgraph(request, graph_id)


# TODO: use prefix ?? (rfield-, ctield-, rtype-)
def _get_available_report_graph_types(ct, name):
    model = ct.model_class()

    try:
        field = model._meta.get_field(name)
    except FieldDoesNotExist:
        if name.isdigit():
            try:
                cf = CustomField.objects.get(pk=name, content_type=ct)
            except CustomField.DoesNotExist:
                logger.debug('get_available_report_graph_types(): "%s" is not a field or a CustomField id', name)
            else:
                field_type = cf.field_type

                if field_type == CustomField.DATETIME:
                    return RGT_CUSTOM_DAY, RGT_CUSTOM_MONTH, RGT_CUSTOM_YEAR, RGT_CUSTOM_RANGE

                if field_type == CustomField.ENUM:
                    return (RGT_CUSTOM_FK,)

                logger.debug('get_available_report_graph_types(): only ENUM & DATETIME CustomField are allowed.')
        else:
            try:
                RelationType.objects.get(pk=name)
            except RelationType.DoesNotExist:
                logger.debug('get_available_report_graph_types(): "%s" is not a field or a RelationType id', name)
            else:
                # TODO: check compatible ??
                return (RGT_RELATION,)
    else:
        if isinstance(field, (DateField, DateTimeField)):
            return RGT_DAY, RGT_MONTH, RGT_YEAR, RGT_RANGE

        if isinstance(field, ForeignKey):
            return (RGT_FK,)

        logger.debug('get_available_report_graph_types(): "%s" is not a valid field for abscissa', name)


# TODO: can be factorised with ReportGraphForm (use ReportGraphHand)
@utils.jsonify
# @permission_required('reports') ??
def get_available_report_graph_types(request, ct_id):
    ct = utils.get_ct_or_404(ct_id)
    abscissa_field = utils.get_from_POST_or_404(request.POST, 'record_id')  # TODO: POST ??!
    gtypes = _get_available_report_graph_types(ct, abscissa_field)

    if gtypes is None:
        result = [{'id': '', 'text': ugettext(u'Choose an abscissa field')}]  # TODO: is the translation useful ??
    else:
        result = [{'id':   type_id,
                   'text': str(RGRAPH_HANDS_MAP[type_id].verbose_name),
                  } for type_id in gtypes
                 ]

    return {'result': result}


def cast_order(order):
    # if order != 'ASC' and order != 'DESC':
    if order not in {'ASC', 'DESC'}:
        raise ValueError('Order must be in {"ASC", "DESC"}')

    return order


@utils.jsonify
# @permission_required('reports') ??
# def fetch_graph(request, graph_id, order=None):
def fetch_graph(request, graph_id):
    order = utils.get_from_GET_or_404(request.GET, 'order', cast=cast_order, default='ASC')
    x, y = get_object_or_404(ReportGraph, pk=graph_id).fetch(order=order)

    return {'x': x, 'y': y, 'graph_id': graph_id}  # TODO: graph_id useful ??


def fetch_graph_from_instanceblock(request, instance_block_id, entity_id):
    warnings.warn('reports.views.graph.fetch_graph_from_instanceblock() is deprecated ; '
                  'use fetch_graph_from_instancebrick() instead.',
                  DeprecationWarning
                 )

    return fetch_graph_from_instancebrick(request, instance_brick_id=instance_block_id, entity_id=entity_id)


@utils.jsonify
# @permission_required('reports') ??
def fetch_graph_from_instancebrick(request, instance_brick_id, entity_id):
    order = utils.get_from_GET_or_404(request.GET, 'order', cast=cast_order, default='ASC')
    instance_brick = get_object_or_404(InstanceBrickConfigItem, pk=instance_brick_id)
    entity = get_object_or_404(CremeEntity, pk=entity_id).get_real_entity()
    # x, y = ReportGraph.get_fetcher_from_instance_block(instance_brick).fetch_4_entity(entity, order)
    x, y = ReportGraph.get_fetcher_from_instance_brick(instance_brick).fetch_4_entity(entity, order)

    # TODO: send error too ?
    return {'x': x, 'y': y}


# Class-based views  ----------------------------------------------------------


class ReportGraphDetail(generic.detailview.EntityDetail):
    model = ReportGraph
    template_name = 'reports/view_graph.html'
    pk_url_kwarg = 'graph_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['report_charts'] = report_chart_registry

        return context
