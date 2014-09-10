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

from django.db.models import FieldDoesNotExist, DateField, DateTimeField, ForeignKey
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views.generic import view_entity, add_to_entity, edit_related_to_entity
from creme.creme_core.models import CremeEntity, InstanceBlockConfigItem, RelationType, CustomField
from creme.creme_core.utils import jsonify, get_ct_or_404, get_from_POST_or_404

from ..constants import *
from ..core.graph import RGRAPH_HANDS_MAP # fetch_graph_from_instance_block
from ..forms.graph import ReportGraphForm
from ..models import ReportGraph


logger = logging.getLogger(__name__)

@login_required
@permission_required('reports')
def add(request, report_id):
    return add_to_entity(request, report_id, ReportGraphForm,
                         _(u'Add a graph for <%s>'),
                        )

@login_required
@permission_required('reports')
def edit(request, graph_id):
    return edit_related_to_entity(request, graph_id, ReportGraph,
                                  ReportGraphForm, _(u'Edit a graph for <%s>'),
                                 )

@login_required
@permission_required('reports')
def detailview(request, graph_id):
    return view_entity(request, graph_id, ReportGraph, '/reports/report', 'reports/view_graph.html',
                       #extra_template_dict={'user_can_admin_report': request.user.has_perm('reports.can_admin'),
                                           #}
                      )

#TODO: use prefix ?? (rfield-, ctield-, rtype-)
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
                     return (RGT_CUSTOM_DAY, RGT_CUSTOM_MONTH, RGT_CUSTOM_YEAR, RGT_CUSTOM_RANGE)

                if field_type == CustomField.ENUM:
                    return (RGT_CUSTOM_FK,)

                logger.debug('get_available_report_graph_types(): only ENUM & DATETIME CustomField are allowed.')
        else:
            try:
                RelationType.objects.get(pk=name)
            except RelationType.DoesNotExist:
                logger.debug('get_available_report_graph_types(): "%s" is not a field or a RelationType id', name)
            else:
                #TODO: check compatible ??
                return (RGT_RELATION,)
    else:
        if isinstance(field, (DateField, DateTimeField)):
            return (RGT_DAY, RGT_MONTH, RGT_YEAR, RGT_RANGE)

        if isinstance(field, ForeignKey):
            return (RGT_FK,)

        logger.debug('get_available_report_graph_types(): "%s" is not a valid field for abscissa', name)

#TODO: can be factorised with ReportGraphForm (use ReportGraphHand)
@jsonify
#@permission_required('reports') ??
def get_available_report_graph_types(request, ct_id):
    ct = get_ct_or_404(ct_id)
    abscissa_field = get_from_POST_or_404(request.POST, 'record_id') #TODO: POST ??!
    gtypes = _get_available_report_graph_types(ct, abscissa_field)

    if gtypes is None:
        result = [{'id': '', 'text': ugettext(u'Choose an abscissa field')}] #TODO: is the translation useful ??
    else:
        result = [{'id':   type_id,
                   'text': unicode(RGRAPH_HANDS_MAP[type_id].verbose_name),
                  } for type_id in gtypes
                 ]

    return {'result': result}

def _check_order(order):
    if order != 'ASC' and order != 'DESC':
        raise Http404('Order must be in ("ASC", "DESC")')

@jsonify
#@permission_required('reports') ??
def fetch_graph(request, graph_id, order):
    _check_order(order)

    x, y = get_object_or_404(ReportGraph, pk=graph_id).fetch(order=order)

    return {'x': x, 'y': y, 'graph_id': graph_id} #TODO: graph_id useful ??

@jsonify
#@permission_required('reports') ??
def fetch_graph_from_instanceblock(request, instance_block_id, entity_id, order):
    _check_order(order)

    instance_block = get_object_or_404(InstanceBlockConfigItem, pk=instance_block_id)
    entity = get_object_or_404(CremeEntity, pk=entity_id).get_real_entity()
    #x, y = fetch_graph_from_instance_block(instance_block, entity, order=order)
    x, y, error = ReportGraph.fetch_from_instance_block(instance_block, entity, order=order)

    #TODO: send error too ?
    return {'x': x, 'y': y}
