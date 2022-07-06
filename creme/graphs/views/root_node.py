################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

from django.utils.translation import gettext_lazy as _

from creme.creme_core.views import generic

from .. import get_graph_model
from ..forms import root_node as forms
from ..models import RootNode


class RootNodesAdding(generic.RelatedToEntityFormPopup):
    form_class = forms.AddRootNodesForm
    template_name = 'creme_core/generics/blockform/link-popup.html'
    title = _('Add root nodes to «{entity}»')
    entity_id_url_kwarg = 'graph_id'
    entity_classes = get_graph_model()
    # submit_label = _('Add') ??


class RootNodeEdition(generic.RelatedToEntityEditionPopup):
    model = RootNode
    form_class = forms.EditRootNodeForm
    permissions = 'graphs'
    pk_url_kwarg = 'root_id'
    title = _('Edit root node for «{entity}»')


class RootNodeDeletion(generic.CremeModelDeletion):
    model = RootNode
    permissions = 'graphs'

    def check_instance_permissions(self, instance, user):
        user.has_perm_to_change_or_die(instance.graph)
