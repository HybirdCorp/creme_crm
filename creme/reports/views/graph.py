# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.db.models import FieldDoesNotExist, DateField, DateTimeField, ForeignKey
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404
from django.template.context import RequestContext
from django.utils.translation import ugettext_lazy as _

from creme_core.views.generic import inner_popup, view_entity, add_to_entity, edit_related_to_entity
from creme_core.models import CremeEntity, InstanceBlockConfigItem
from creme_core.utils import jsonify, get_ct_or_404

from reports.models.report import Report
from reports.models.graph import (ReportGraph, verbose_report_graph_types,
                                  RGT_FK, RGT_RANGE, RGT_YEAR, RGT_MONTH, RGT_DAY,
                                  fetch_graph_from_instance_block)
from reports.forms.graph import ReportGraphAddForm

@login_required
@permission_required('reports')
def add(request, report_id):
    return add_to_entity(request, report_id, ReportGraphAddForm,
                             _(u'Add a graph for <%s>'),
                            )

@login_required
@permission_required('reports')
def edit(request, graph_id):
    return edit_related_to_entity(request, graph_id, ReportGraph, ReportGraphAddForm, _(u'Edit a graph for <%s>'))

@login_required
@permission_required('reports')
def detailview(request, graph_id):
    return view_entity(request, graph_id, ReportGraph, '/reports/report', 'reports/view_graph.html',
                       extra_template_dict={'verbose_report_graph_types': verbose_report_graph_types,
                                            'user_can_admin_report': request.user.has_perm('reports.can_admin')}
                      )

@jsonify
#@permission_required('reports') ??
def get_available_report_graph_types(request, ct_id):
    ct = get_ct_or_404(ct_id)
    model = ct.model_class()

    abscissa_field = request.POST.get('record_id')

    field = None
    result = [{'id': '', 'text': _(u'Choose an abscissa field')}]

    try:
        field = model._meta.get_field(abscissa_field)
    except FieldDoesNotExist:
        pass

    #TODO: factorise 'if field'
    if field and isinstance(field, (DateField, DateTimeField)):
        verbose_report_graph_types_get = verbose_report_graph_types.get
        result = [{'id': type_id, 'text': unicode(verbose_report_graph_types_get(type_id))} for type_id in [RGT_DAY, RGT_MONTH, RGT_YEAR, RGT_RANGE]]
    elif field and isinstance(field, ForeignKey):
        result = [{'id': RGT_FK, 'text': unicode(verbose_report_graph_types.get(RGT_FK))}]

    return {'result': result}

@jsonify
#@permission_required('reports') ??
def fetch_graph(request, graph_id, order):
    graph = get_object_or_404(ReportGraph, pk=graph_id)

    x, y = graph.fetch(order=order)

    return {'x': x, 'y': y, 'graph_id': graph_id}

@jsonify
#@permission_required('reports') ??
def fetch_graph_from_instanceblock(request, instance_block_id, entity_id, order):
    instance_block = get_object_or_404(InstanceBlockConfigItem, pk=instance_block_id)
    entity = get_object_or_404(CremeEntity, pk=entity_id).get_real_entity()

    x, y = fetch_graph_from_instance_block(instance_block, entity, order=order)

    return {'x': x, 'y': y}
