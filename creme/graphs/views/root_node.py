# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required, permission_required

from creme_core.views.generic import add_to_entity, edit_related_to_entity
from creme_core.utils import get_from_POST_or_404

from graphs.models import Graph, RootNode
from graphs.forms.root_node import AddRootNodesForm, EditRootNodeForm


@login_required
@permission_required('graphs')
def add(request, graph_id):
    return add_to_entity(request, graph_id, AddRootNodesForm,
                         _(u'Add root nodes to <%s>'), entity_class=Graph
                        )

@login_required
@permission_required('graphs')
def edit(request, root_id):
    return edit_related_to_entity(request, root_id, RootNode, EditRootNodeForm, _(u'Edit root node for <%s>'))

@login_required
@permission_required('graphs')
def delete(request):
    root_node = get_object_or_404(RootNode, pk=get_from_POST_or_404(request.POST, 'id'))

    root_node.graph.can_change_or_die(request.user)
    root_node.delete()

    return HttpResponse("", mimetype="text/javascript")
