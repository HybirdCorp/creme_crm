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

from django.template import RequestContext
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404, render_to_response
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required

from creme_core.entities_access.functions_for_permissions import get_view_or_die, edit_object_or_die
from creme_core.views.generic import inner_popup
from creme_core.utils import get_from_POST_or_404

from graphs.models import Graph, RootNode
from graphs.forms.root_node import AddRootNodesForm, EditRootNodeForm


 #TODO: no inner_popup because GenericEntitiesField doesn't work with inner_popup ;(
@login_required
@get_view_or_die('graphs')
def add(request, graph_id):
    graph = get_object_or_404(Graph, pk=graph_id)

    die_status = edit_object_or_die(request, graph)
    if die_status:
        return die_status

    if request.POST:
        nodes_form = AddRootNodesForm(graph, request.POST)

        if nodes_form.is_valid():
            nodes_form.save()

            return HttpResponseRedirect(graph.get_absolute_url()) ###
    else:
        nodes_form = AddRootNodesForm(graph=graph)

    #return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       #{
                        #'form':   nodes_form,
                        #'title':  _(u'Add root nodes'),
                       #},
                       #is_valid=nodes_form.is_valid(),
                       #reload=False,
                       #delegate_reload=True,
                       #context_instance=RequestContext(request))

    return render_to_response('creme_core/generics/blockform/add.html',
                              {
                                'form': nodes_form,
                              },
                              context_instance=RequestContext(request))

@login_required
@get_view_or_die('graphs')
def edit(request, root_id):
    root_node = get_object_or_404(RootNode, pk=root_id)
    graph     = root_node.graph

    die_status = edit_object_or_die(request, graph)
    if die_status:
        return die_status

    if request.POST:
        nodes_form = EditRootNodeForm(request.POST, instance=root_node)

        if nodes_form.is_valid():
            nodes_form.save()
    else:
        nodes_form = EditRootNodeForm(instance=root_node)

    return inner_popup(request, 'creme_core/generics/blockform/edit_popup.html',
                       {
                        'form':   nodes_form,
                        'title':  _(u'Edit root node for <%s>') % graph,
                       },
                       is_valid=nodes_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))

@login_required
@get_view_or_die('graphs')
def delete(request):
    root_node = get_object_or_404(RootNode, pk=get_from_POST_or_404(request.POST, 'id'))

    die_status = edit_object_or_die(request, root_node.graph)
    if die_status:
        return die_status

    root_node.delete()

    return HttpResponse("", mimetype="text/javascript")
