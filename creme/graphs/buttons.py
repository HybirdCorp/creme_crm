################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2026  Hybird
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

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.gui.button_menu import Button

from . import get_graph_model
from .core import InstanceBrickMixin


class CreateInstanceBrickButton(InstanceBrickMixin, Button):
    id = Button.generate_id('graphs', 'create_instance_brick')
    verbose_name = _('Create a block')
    description = _(
        'This button creates a new type of block which displays the current Graph.\n'
        'It becomes available in the configuration of blocks to be set on Home & «My Page».\n'
        'App: Graphs'
    )
    dependencies = (get_graph_model(),)
    template_name = 'graphs/buttons/create-instance-brick.html'
    permissions = 'graphs.can_admin'

    def get_context(self, *, entity, request):
        ctxt = super().get_context(entity=entity, request=request)

        try:
            self.no_brick_instance_or_die(graph=entity)
        except ConflictError as e:
            ctxt['permission_error'] = str(e)

        return ctxt

    def get_ctypes(self):
        return self.dependencies
