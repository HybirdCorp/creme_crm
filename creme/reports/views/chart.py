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

from django.http.response import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from creme import reports
from creme.creme_core.http import CremeJsonResponse
from creme.creme_core.utils.meta import Order
from creme.creme_core.views import generic
from creme.creme_core.views.bricks import BricksReloading

from ..bricks import ReportChartBrick
from ..core.chart import plot
from ..forms.chart import ChartForm
from ..models import ReportChart

logger = logging.getLogger(__name__)


class ChartCreation(generic.AddingInstanceToEntityPopup):
    model = ReportChart
    form_class = ChartForm
    title = _('Create a chart for «{entity}»')
    entity_id_url_kwarg = 'report_id'
    entity_classes = reports.get_report_model()


class ChartDetail(generic.CremeModelDetail):
    model = ReportChart
    template_name = 'reports/view_chart.html'
    pk_url_kwarg = 'chart_id'
    permissions = 'reports'  # TODO: test
    bricks_reload_url_name = 'reports__reload_chart_bricks'
    # TODO: 'main' & 'hat'?
    bricks = [ReportChartBrick]

    def get_bricks(self):
        return {'main': [brick_cls() for brick_cls in self.bricks]}


# TODO: factorise with other reloading views?
class ChartDetailBricksReloading(BricksReloading):
    chart_id_url_kwarg = 'chart_id'
    permissions = 'reports'  # TODO: test
    bricks = ChartDetail.bricks

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chart = None

    def get_bricks(self):
        reloaded_bricks = []
        allowed_bricks = {brick_cls.id: brick_cls for brick_cls in self.bricks}

        for brick_id in self.get_brick_ids():
            try:
                brick_cls = allowed_bricks[brick_id]
            except KeyError as e:
                raise Http404(f'Invalid brick id "{brick_id}"') from e

            reloaded_bricks.append(brick_cls())

        return reloaded_bricks

    def get_bricks_context(self):
        context = super().get_bricks_context()
        context['object'] = self.get_chart()

        return context

    def get_chart(self):
        chart = self.chart

        if chart is None:
            self.chart = chart = get_object_or_404(
                ReportChart, id=self.kwargs[self.chart_id_url_kwarg],
            )
            self.request.user.has_perm_to_view_or_die(chart)  # TODO: test

        return chart


class ChartEdition(generic.RelatedToEntityEditionPopup):
    model = ReportChart
    form_class = ChartForm
    permissions = 'reports'
    pk_url_kwarg = 'chart_id'
    title = _('Edit a chart for «{entity}»')


class ChartDeletion(generic.CremeModelDeletion):
    model = ReportChart
    pk_url_kwarg = 'chart_id'

    def check_instance_permissions(self, instance, user):
        user.has_perm_to_change_or_die(instance)  # NB: get_related_entity() is used

    def get_query_kwargs(self):
        return {'id': self.kwargs[self.pk_url_kwarg]}


class ChartFetchSettingsUpdate(generic.base.CheckedView):
    # permissions = 'reports' => No, we want to get the "plot" even if the ReportChart
    #                            cannot be seen (the plot's data use credentials any way).
    response_class = CremeJsonResponse
    chart_id_url_kwarg = 'chart_id'
    plot_registry = plot.plot_registry

    def clean_plot(self, request):
        plot_name = request.POST.get('plot')

        if not plot_name:
            raise ValueError('Plot name is missing')

        if self.plot_registry.get(plot_name) is None:
            raise ValueError(
                f'Plot name must be in {[plot.name for plot in self.plot_registry]} '
                f'(given name="{plot_name}")'
            )

        return plot_name

    def clean_sort(self, request):
        value = request.POST.get('sort', 'ASC')
        return Order.from_string(value)

    def get_chart(self, request) -> ReportChart:
        return get_object_or_404(ReportChart, id=self.kwargs[self.chart_id_url_kwarg])

    def post(self, request, *args, **kwargs):
        try:
            plot_name: str = self.clean_plot(request)
            order: Order = self.clean_sort(request)
        except ValueError as e:
            return HttpResponseBadRequest(e)

        chart = self.get_chart(request)

        if request.user.has_perm_to_change(chart):
            # TODO: does need we a 'default' plot value?
            if plot_name != chart.plot_name or order.asc != chart.asc:
                type(chart).objects.filter(id=chart.id).update(
                    asc=order.asc, plot_name=plot_name,
                )
        else:
            order = Order(chart.asc)
            plot_name = chart.plot_name

            logger.warning(
                'The ReportChart id="%s" cannot be edited, so the settings '
                'are not saved.', chart.id,
            )

        # TODO: send error too ?
        return self.response_class({'sort': str(order), 'plot': plot_name})
