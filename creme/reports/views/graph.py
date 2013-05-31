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

import logging

from django.db.models import FieldDoesNotExist, DateField, DateTimeField, ForeignKey
from django.contrib.auth.decorators import login_required, permission_required
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.views.generic import view_entity, add_to_entity, edit_related_to_entity
from creme.creme_core.models import CremeEntity, InstanceBlockConfigItem, RelationType
from creme.creme_core.utils import jsonify, get_ct_or_404, get_from_POST_or_404

from ..models.graph import (ReportGraph, verbose_report_graph_types,
                            RGT_FK, RGT_RANGE, RGT_YEAR, RGT_MONTH, RGT_DAY,
                            RGT_RELATION, fetch_graph_from_instance_block)
from ..forms.graph import ReportGraphForm


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
                       extra_template_dict={'verbose_report_graph_types': verbose_report_graph_types,
                                            'user_can_admin_report':      request.user.has_perm('reports.can_admin'),
                                           }
                      )

#TODO: can be factorised with ReportGraphForm (better graph type system)
@jsonify
#@permission_required('reports') ??
def get_available_report_graph_types(request, ct_id):
    ct = get_ct_or_404(ct_id)
    model = ct.model_class()

    #abscissa_field = request.POST.get('record_id')
    abscissa_field = get_from_POST_or_404(request.POST, 'record_id') #TODO: POST ??!

    field = None
    result = [{'id': '', 'text': ugettext(u'Choose an abscissa field')}] #TODO: is the translation useful ??

    try:
        field = model._meta.get_field(abscissa_field)
    except FieldDoesNotExist:
        #Assume the field is a relation
        try:
            RelationType.objects.get(pk=abscissa_field)
        except RelationType.DoesNotExist:
            logger.debug('get_available_report_graph_types(): "%s" is not a field or a RelationType id', abscissa_field)
        else:
            #TODO: check compatible ??
            result = [{'id': RGT_RELATION, 'text': unicode(verbose_report_graph_types.get(RGT_RELATION))}]
    else:
        if isinstance(field, (DateField, DateTimeField)):
            verbose_report_graph_types_get = verbose_report_graph_types.get
            result = [{'id': type_id, 'text': unicode(verbose_report_graph_types_get(type_id))}
                        for type_id in (RGT_DAY, RGT_MONTH, RGT_YEAR, RGT_RANGE)
                     ]
        elif isinstance(field, ForeignKey):
            result = [{'id': RGT_FK, 'text': unicode(verbose_report_graph_types.get(RGT_FK))}]
        else:
            logger.debug('get_available_report_graph_types(): "%s" is not a valid field for abscissa', abscissa_field)

    return {'result': result}

def _check_order(order):
    if order != 'ASC' and order != 'DESC':
        raise Http404('Order must be in ("ASC", "DESC")')

@jsonify
#@permission_required('reports') ??
def fetch_graph(request, graph_id, order):
    _check_order(order)

    x, y = get_object_or_404(ReportGraph, pk=graph_id).fetch(order=order)

    return {'x': x, 'y': y, 'graph_id': graph_id}

@jsonify
#@permission_required('reports') ??
def fetch_graph_from_instanceblock(request, instance_block_id, entity_id, order):
    _check_order(order)

    instance_block = get_object_or_404(InstanceBlockConfigItem, pk=instance_block_id)
    entity = get_object_or_404(CremeEntity, pk=entity_id).get_real_entity()
    x, y = fetch_graph_from_instance_block(instance_block, entity, order=order)

    return {'x': x, 'y': y}
