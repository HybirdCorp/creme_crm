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


from django.db.models.fields import (FieldDoesNotExist, DateField, DateTimeField)
from django.db.models.fields.related import ForeignKey
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from django.template.context import RequestContext
from django.utils.translation import ugettext_lazy as _

from creme_core.entities_access.functions_for_permissions import add_view_or_die, get_view_or_die
from creme_core.views.generic.popup import inner_popup
from creme_core.views.generic.detailview import view_entity_with_template
from creme_core.utils import jsonify, get_ct_or_404
from creme_core.models.entity import CremeEntity
from creme_core.models.block import InstanceBlockConfigItem
from creme.creme_core.utils import jsonify

from reports.models.report import Report, report_prefix_url, report_template_dir
from reports.models.graph import (ReportGraph, verbose_report_graph_types,
                                  RGT_FK, RGT_RANGE, RGT_YEAR, RGT_MONTH, RGT_DAY,
                                  fetch_graph_from_instance_block)
from reports.forms.graph import ReportGraphAddForm


report_graph_app = ReportGraph._meta.app_label
report_graph_ct  = ContentType.objects.get_for_model(ReportGraph)

@login_required
@get_view_or_die(report_graph_app)
@add_view_or_die(report_graph_ct, None, report_graph_app)
def add(request, report_id):
    report = get_object_or_404(Report, pk=report_id)
    POST = request.POST
    if POST:
        graph_form = ReportGraphAddForm(report, POST)

        if graph_form.is_valid():
            graph_form.save()
    else:
        graph_form = ReportGraphAddForm(report=report)

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {
                        'form':   graph_form,
                        'title': _(u'Add a graph for <%s>') % report,
                       },
                       is_valid=graph_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))

@login_required
@get_view_or_die(report_graph_app)
@add_view_or_die(report_graph_ct, None, report_graph_app)
def edit(request, graph_id):
    graph = get_object_or_404(ReportGraph, pk=graph_id)
    POST = request.POST
    if POST:
        graph_form = ReportGraphAddForm(graph.report, POST, instance=graph)

        if graph_form.is_valid():
            graph_form.save()
    else:
        graph_form = ReportGraphAddForm(report=graph.report, instance=graph)

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {
                        'form':   graph_form,
                        'title': _(u'Edit a graph for <%s>') % graph.report,
                       },
                       is_valid=graph_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))


@login_required
@get_view_or_die(report_graph_app)
def detailview(request, graph_id):
    """
        @Permissions : Acces or Admin to document app & Read on current ReportGraph object
    """
    return view_entity_with_template(request, graph_id, ReportGraph,
                                     '%s/report' % report_prefix_url,
                                     '%s/view_graph.html' % report_template_dir,
                                     extra_template_dict={'verbose_report_graph_types': verbose_report_graph_types})

@jsonify
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

    if field and isinstance(field, (DateField, DateTimeField)):
        verbose_report_graph_types_get = verbose_report_graph_types.get
        result = [{'id': type_id, 'text': unicode(verbose_report_graph_types_get(type_id))} for type_id in [RGT_DAY, RGT_MONTH, RGT_YEAR, RGT_RANGE]]
    elif field and isinstance(field, ForeignKey):
        result = [{'id': RGT_FK, 'text': unicode(verbose_report_graph_types.get(RGT_FK))}]

    return {'result': result}

@jsonify
def fetch_graph(request, graph_id, order):
    graph = get_object_or_404(ReportGraph, pk=graph_id)

    x, y = graph.fetch(order=order)

    return {'x': x, 'y': y, 'graph_id': graph_id}

@jsonify
def fetch_graph_from_instanceblock(request, instance_block_id, entity_id, order):
    instance_block = get_object_or_404(InstanceBlockConfigItem, pk=instance_block_id)
    entity = get_object_or_404(CremeEntity, pk=entity_id).get_real_entity()
    
    x, y = fetch_graph_from_instance_block(instance_block, entity, order=order)

    return {'x': x, 'y': y}
