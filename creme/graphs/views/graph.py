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

from django.http import HttpResponse
from django.template import RequestContext
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType

from creme_core.entities_access.functions_for_permissions import add_view_or_die, get_view_or_die, read_object_or_die, edit_object_or_die
from creme_core.views.generic import add_entity, view_entity_with_template, edit_entity, list_view, inner_popup

from graphs.models import Graph
from graphs.forms.graph import GraphForm, AddRelationTypesForm


@login_required
@get_view_or_die('graphs')
@add_view_or_die(ContentType.objects.get_for_model(Graph), None, 'graphs')
def add(request):
    return add_entity(request, GraphForm)

@login_required
@get_view_or_die('graphs')
def dl_png(request, graph_id):
    graph = get_object_or_404(Graph, pk=graph_id)

    die_status = read_object_or_die(request, graph)
    if die_status:
        return die_status

    return graph.generate_png()

def edit(request, graph_id):
    return edit_entity(request, graph_id, Graph, GraphForm, 'graphs')

@login_required
@get_view_or_die('graphs')
def detailview(request, graph_id):
    return view_entity_with_template(request, graph_id, Graph, '/graphs/graph', 'graphs/view_graph.html')

@login_required
@get_view_or_die('graphs')
def listview(request):
    return list_view(request, Graph, extra_dict={'add_url':'/graphs/graph/add'})

@login_required
@get_view_or_die('graphs')
def add_relation_types(request, graph_id):
    graph = get_object_or_404(Graph, pk=graph_id)

    die_status = edit_object_or_die(request, graph)
    if die_status:
        return die_status

    if request.POST:
        rtypes_form = AddRelationTypesForm(graph, request.POST)

        if rtypes_form.is_valid():
            rtypes_form.save()
    else:
        rtypes_form = AddRelationTypesForm(graph)

    return inner_popup(request, 'creme_core/generics/blockform/edit_popup.html',
                       {
                        'form':   rtypes_form,
                        'title':  _(u'Add relation types to <%s>') % graph,
                       },
                       is_valid=rtypes_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))

@login_required
@get_view_or_die('graphs')
def delete_relation_type(request, graph_id):
    graph = get_object_or_404(Graph, pk=graph_id)

    die_status = edit_object_or_die(request, graph)
    if die_status:
        return die_status

    graph.orbital_relation_types.remove(request.POST.get('id'))

    return HttpResponse("", mimetype="text/javascript")
