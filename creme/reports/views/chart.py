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

import logging

from django.http.response import HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from creme import reports
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.gui.bricks import brick_registry
from creme.creme_core.http import CremeJsonResponse
from creme.creme_core.models import InstanceBrickConfigItem
from creme.creme_core.utils.meta import Order
from creme.creme_core.views import generic
from creme.creme_core.views.generic import base

from ..forms.chart import ChartForm
from ..models import ReportChart
from ..report_chart_registry import report_chart_registry

logger = logging.getLogger(__name__)


class ChartCreation(generic.AddingInstanceToEntityPopup):
    model = ReportChart
    form_class = ChartForm
    title = _('Create a chart for «{entity}»')
    entity_id_url_kwarg = 'report_id'
    entity_classes = reports.get_report_model()


class ChartDetail(generic.EntityDetail):
    model = ReportChart
    template_name = 'reports/view_chart.html'
    pk_url_kwarg = 'chart_id'
    report_chart_registry = report_chart_registry  # TODO

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['report_charts'] = self.report_chart_registry  # TODO

        return context


class ChartEdition(generic.RelatedToEntityEditionPopup):
    model = ReportChart
    form_class = ChartForm
    permissions = 'reports'
    pk_url_kwarg = 'chart_id'
    title = _('Edit a chart for «{entity}»')


class ChartFetchSettingsBase(base.CheckedView):
    # permissions = 'reports' => No, we want to get the "plot" even if the ReportChart
    #                            cannot be seen (the plot's data use credentials any way).
    response_class = CremeJsonResponse
    report_chart_registry = report_chart_registry  # TODO

    def clean_chart(self, request):  # TODO: rename
        value = request.POST.get('chart')  # TODO: rename

        if not value:
            raise ValueError('Chart value is missing')

        registered = [c[0] for c in self.report_chart_registry]

        if value not in registered:
            raise ValueError(
                f'Chart value must be in {registered} (value={value})'
            )

        return value

    def clean_sort(self, request):
        value = request.POST.get('sort', 'ASC')
        return Order.from_string(value)

    def post(self, request, *args, **kwargs):
        try:
            chart: str = self.clean_chart(request)  # TODO: rename
            order: Order = self.clean_sort(request)
        except ValueError as e:
            return HttpResponseBadRequest(e)

        rgraph = self.get_graph(request)  # TODO: rename

        if self.request.user.has_perm_to_change(rgraph):
            # TODO: does need we a 'default' chart value ??
            if (chart and chart != rgraph.chart) or order.asc != rgraph.asc:
                type(rgraph).objects.filter(id=rgraph.id).update(
                    asc=order.asc,
                    chart=chart
                )
        else:
            order = Order(rgraph.asc)
            chart = rgraph.chart

            logger.warning(
                'The ReportGraph id="%s" cannot be edited, '
                'so the settings are not saved.',
                rgraph.id
            )

        # TODO: send error too ?
        return self.response_class({'sort': str(order), 'chart': chart})


class ChartFetchSettings(base.EntityRelatedMixin, ChartFetchSettingsBase):
    entity_id_url_kwarg = 'chart_id'
    entity_classes = ReportChart

    def check_related_entity_permissions(self, entity, user):
        # NB: we avoid the <user.has_perm_to_change_or_die(entity)> of super().
        #     (see ChartFetchingBase notes about credentials).
        pass

    def get_graph(self, request):  # TODO: rename
        return self.get_related_entity()


# TODO: rework
class ChartFetchSettingsForInstance(base.EntityRelatedMixin, ChartFetchSettingsBase):
    def get_graph(self, request):  # TODO: rename
        entity = self.get_related_entity()
        brick_config = get_object_or_404(
            InstanceBrickConfigItem,
            pk=self.kwargs['instance_brick_id'],
        )
        brick = brick_registry.get_brick_4_instance(brick_config, entity=entity)

        try:
            return brick.fetcher.graph
        except AttributeError as e:
            raise ConflictError('Invalid brick: {e}') from e  # TODO: test
