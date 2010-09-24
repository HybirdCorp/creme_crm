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

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.template.context import RequestContext
from django.utils.translation import ugettext_lazy as _

from creme_core.entities_access.functions_for_permissions import add_view_or_die, get_view_or_die
from creme_core.views.generic.popup import inner_popup
from reports.forms.blocks import GraphInstanceBlockForm
from reports.models.graph import ReportGraph
from reports.views.graph import report_graph_app, report_graph_ct

#TODO: use add_to_entity() genreic view

@login_required
@get_view_or_die(report_graph_app)
@add_view_or_die(report_graph_ct, None, report_graph_app)
def add_graph_instance_block(request, graph_id):
    graph = get_object_or_404(ReportGraph, pk=graph_id)
    POST = request.POST
    if POST:
        graph_form = GraphInstanceBlockForm(graph, POST)

        if graph_form.is_valid():
            graph_form.save()
    else:
        graph_form = GraphInstanceBlockForm(graph=graph)

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {
                        'form':   graph_form,
                        'title': _(u'Add an instance block for <%s>') % graph,
                       },
                       is_valid=graph_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))