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


class ChartDetail(generic.EntityDetail):
    model = ReportChart
    template_name = 'reports/view_chart.html'
    pk_url_kwarg = 'chart_id'
    plot_registry = plot.plot_registry

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # context['report_charts'] = self.report_chart_registry
        context['plots'] = [*self.plot_registry]  # TODO: FIX TEMPLATE !!!!!!!!!!!!!!!!!!!!!!!

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
    plot_registry = plot.plot_registry

    def clean_plot(self, request):
        plot_name = request.POST.get('plot')  # TODO: FIX test & view/JS

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
        raise NotImplementedError

    def post(self, request, *args, **kwargs):
        try:
            plot_name: str = self.clean_plot(request)
            order: Order = self.clean_sort(request)
        except ValueError as e:
            return HttpResponseBadRequest(e)

        chart = self.get_chart(request)

        if self.request.user.has_perm_to_change(chart):
            # TODO: does need we a 'default' chart value ??
            if plot_name != chart.plot_name or order.asc != chart.asc:
                type(chart).objects.filter(id=chart.id).update(
                    asc=order.asc, plot_name=plot_name,
                )
        else:
            order = Order(chart.asc)
            plot_name = chart.plot_name

            logger.warning(
                'The ReportChart id="%s" cannot be edited, '
                'so the settings are not saved.',
                chart.id,
            )

        # TODO: send error too ?
        return self.response_class({'sort': str(order), 'plot': plot_name})


# TODO: rework (change base class etc...)
class ChartFetchSettings(base.EntityRelatedMixin, ChartFetchSettingsBase):
    entity_id_url_kwarg = 'chart_id'
    entity_classes = ReportChart

    def check_related_entity_permissions(self, entity, user):
        # NB: we avoid the <user.has_perm_to_change_or_die(entity)> of super().
        #     (see ChartFetchingBase notes about credentials).
        pass

    def get_chart(self, request):
        return self.get_related_entity()    # TODO: nope !!!!!!!!!!!!!!!!


# TODO: rework (change base class etc...)
class ChartFetchSettingsForInstance(base.EntityRelatedMixin, ChartFetchSettingsBase):
    def get_chart(self, request):
        entity = self.get_related_entity()    # TODO: nope !!!!!!!!!!!!!!!!
        brick_config = get_object_or_404(
            InstanceBrickConfigItem,
            pk=self.kwargs['instance_brick_id'],
        )
        brick = brick_registry.get_brick_4_instance(brick_config, entity=entity)

        try:
            return brick.fetcher.chart
        except AttributeError as e:
            raise ConflictError('Invalid brick: {e}') from e  # TODO: test
