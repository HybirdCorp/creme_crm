# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.auth.decorators import (
    login_required,
    permission_required,
)
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic

from .. import custom_forms, get_graph_model
from ..constants import DEFAULT_HFILTER_GRAPH
from ..forms.graph import AddRelationTypesForm

Graph = get_graph_model()


@login_required
@permission_required('graphs')
def dl_png(request, graph_id):
    graph = get_object_or_404(Graph, pk=graph_id)
    user = request.user

    user.has_perm_to_view_or_die(graph)

    try:
        return graph.generate_png(user)
    except ImportError:
        return render(
            request, 'graphs/graph_error.html',
            {
                'error_message': gettext(
                    'The package "pygraphviz" is not installed ; '
                    'please contact your administrator.'
                ),
            },
        )
    except Graph.GraphException:
        return render(
            request, 'graphs/graph_error.html',
            {'error_message': gettext('This graph is too big!')},
        )


class RelationTypeRemoving(generic.base.EntityRelatedMixin, generic.CremeDeletion):
    permissions = 'graphs'
    entity_classes = Graph
    entity_id_url_kwarg = 'graph_id'

    rtype_id_arg = 'id'

    def perform_deletion(self, request):
        rtype_id = get_from_POST_or_404(request.POST, self.rtype_id_arg)
        self.get_related_entity().orbital_relation_types.remove(rtype_id)


class GraphCreation(generic.EntityCreation):
    model = Graph
    form_class = custom_forms.GRAPH_CREATION_CFORM


class GraphDetail(generic.EntityDetail):
    model = Graph
    template_name = 'graphs/view_graph.html'
    pk_url_kwarg = 'graph_id'


class GraphEdition(generic.EntityEdition):
    model = Graph
    form_class = custom_forms.GRAPH_EDITION_CFORM
    pk_url_kwarg = 'graph_id'


class GraphsList(generic.EntitiesList):
    model = Graph
    default_headerfilter_id = DEFAULT_HFILTER_GRAPH


class RelationTypesAdding(generic.RelatedToEntityFormPopup):
    form_class = AddRelationTypesForm
    template_name = 'creme_core/generics/blockform/link-popup.html'
    title = _('Add relation types to «{entity}»')
    entity_id_url_kwarg = 'graph_id'
    entity_classes = Graph
