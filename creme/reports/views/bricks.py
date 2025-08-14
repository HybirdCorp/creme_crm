################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

# from creme.creme_core.models import InstanceBrickConfigItem
from creme.creme_core.views import generic

# from .. import get_report_model, get_rgraph_model
from ..bricks import InstanceBricksInfoBrick
# from ..forms.bricks import GraphInstanceBrickForm
from ..forms.bricks import ChartInstanceBrickForm
from ..models import ReportChart
from .chart import ChartDetailBricksReloading


# class GraphInstanceBrickCreation(generic.AddingInstanceToEntityPopup):
#     model = InstanceBrickConfigItem
#     form_class = GraphInstanceBrickForm
#     permissions = 'reports.can_admin'
#     title = _('Create an instance block for «{entity}»')
#     entity_classes = get_rgraph_model()
#     entity_id_url_kwarg = 'graph_id'
#     entity_form_kwarg = 'graph'
#
#     help_message = _(
#         'When you create a block, it becomes available in the blocks configuration. '
#         'It can be displayed on Home, on «My Page» & on the detail-views of entities.'
#     )
#
#     def check_related_entity_permissions(self, entity, user):
#         pass  # NB: only admin credentials are needed
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['help_message'] = self.help_message
#
#         return context
class ChartInstanceBrickCreation(generic.RelatedToEntityEditionPopup):
    model = ReportChart
    form_class = ChartInstanceBrickForm
    permissions = 'reports.can_admin'
    title = _('Create an instance block for «{chart}»')
    pk_url_kwarg = 'chart_id'

    # TODO: method get_help_message() in base class?
    help_message = _(
        'When you create a block, it becomes available in the blocks configuration. '
        'It can be displayed on Home, on «My Page» & on the detail-views of entities.'
    )

    def check_related_entity_permissions(self, entity, user):
        pass  # NB: only admin credentials are needed

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['help_message'] = self.help_message

        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['chart'] = kwargs['instance']

        del kwargs['entity']
        del kwargs['instance']

        return kwargs

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['chart'] = self.object

        return data


# class GraphInstanceBricks(generic.RelatedToEntityDetailPopup):
#     model = get_rgraph_model()
#     pk_url_kwarg = 'graph_id'
#     bricks_reload_url_name = 'creme_core__reload_detailview_bricks'
#
#     def get_brick_ids(self):
#         return (
#             InstanceBricksInfoBrick.id,
#         )
# TODO: factorise
class ChartInstanceBricksInfo(generic.RelatedToEntityDetailPopup):
    model = ReportChart
    pk_url_kwarg = 'chart_id'
    bricks_reload_url_name = 'reports__reload_chart_ibci_bricks'

    bricks = [InstanceBricksInfoBrick]

    def get_bricks(self):
        return {'main': [brick_cls() for brick_cls in self.bricks]}


class ChartInstanceBricksInfoReloading(ChartDetailBricksReloading):
    bricks = ChartInstanceBricksInfo.bricks
