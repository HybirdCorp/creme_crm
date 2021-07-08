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

# import warnings
import logging

# from django.core.exceptions import FieldDoesNotExist
# from django.utils.translation import gettext
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from creme import reports
from creme.creme_core import utils
# from creme.creme_core.auth.decorators import login_required
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.gui.bricks import brick_registry
from creme.creme_core.http import CremeJsonResponse
from creme.creme_core.models import InstanceBrickConfigItem
from creme.creme_core.utils.meta import Order
from creme.creme_core.views import generic
# from creme.creme_core.views.decorators import jsonify
from creme.creme_core.views.generic import base

# from .. import constants
from ..core.graph import GraphFetcher  # RGRAPH_HANDS_MAP
from ..forms.graph import ReportGraphForm
from ..report_chart_registry import report_chart_registry

logger = logging.getLogger(__name__)
ReportGraph = reports.get_rgraph_model()


# Function views --------------------------------------------------------------

# def _get_available_report_graph_types(ct, name):
#     warnings.warn('reports.views.graph._get_available_report_graph_types() is deprecated.',
#                   DeprecationWarning
#                  )
#
#     from django.db.models import DateField, DateTimeField, ForeignKey
#
#     from creme.creme_core.models import CustomField, RelationType
#
#     model = ct.model_class()
#
#     try:
#         field = model._meta.get_field(name)
#     except FieldDoesNotExist:
#         if name.isdigit():
#             try:
#                 cf = CustomField.objects.get(pk=name, content_type=ct)
#             except CustomField.DoesNotExist:
#                 logger.debug(
#                     'get_available_report_graph_types(): '
#                     '"%s" is not a field or a CustomField id',
#                     name
#                 )
#             else:
#                 field_type = cf.field_type
#
#                 if field_type == CustomField.DATETIME:
#                     return (
#                         constants.RGT_CUSTOM_DAY,
#                         constants.RGT_CUSTOM_MONTH,
#                         constants.RGT_CUSTOM_YEAR,
#                         constants.RGT_CUSTOM_RANGE,
#                     )
#
#                 if field_type == CustomField.ENUM:
#                     return (constants.RGT_CUSTOM_FK,)
#
#                 logger.debug(
#                     'get_available_report_graph_types(): '
#                     'only ENUM & DATETIME CustomField are allowed.'
#                 )
#         else:
#             try:
#                 RelationType.objects.get(pk=name)
#             except RelationType.DoesNotExist:
#                 logger.debug(
#                     'get_available_report_graph_types(): '
#                     '"%s" is not a field or a RelationType id', name
#                 )
#             else:
#                 return (constants.RGT_RELATION,)
#     else:
#         if isinstance(field, (DateField, DateTimeField)):
#             return (
#                 constants.RGT_DAY,
#                 constants.RGT_MONTH,
#                 constants.RGT_YEAR,
#                 constants.RGT_RANGE,
#             )
#
#         if isinstance(field, ForeignKey):
#             return (constants.RGT_FK,)
#
#         logger.debug(
#             'get_available_report_graph_types(): "%s" is not a valid field for abscissa', name
#         )


# @login_required
# @jsonify
# def get_available_report_graph_types(request, ct_id):
#     warnings.warn('reports.views.graph.get_available_report_graph_types() is deprecated.',
#                   DeprecationWarning
#                  )
#
#     ct = utils.get_ct_or_404(ct_id)
#     abscissa_field = utils.get_from_POST_or_404(request.POST, 'record_id')
#     gtypes = _get_available_report_graph_types(ct, abscissa_field)
#
#     if gtypes is None:
#         result = [{'id': '', 'text': gettext('Choose an abscissa field')}]
#     else:
#         result = [{'id':   type_id,
#                    'text': str(RGRAPH_HANDS_MAP[type_id].verbose_name),
#                   } for type_id in gtypes
#                  ]
#
#     return {'result': result}


# Class-based views  ----------------------------------------------------------


class GraphCreation(generic.AddingInstanceToEntityPopup):
    model = ReportGraph
    form_class = ReportGraphForm
    title = _('Create a graph for «{entity}»')
    entity_id_url_kwarg = 'report_id'
    entity_classes = reports.get_report_model()


class GraphDetail(generic.EntityDetail):
    model = ReportGraph
    template_name = 'reports/view_graph.html'
    pk_url_kwarg = 'graph_id'
    report_chart_registry = report_chart_registry

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['report_charts'] = self.report_chart_registry

        return context


class GraphEdition(generic.RelatedToEntityEditionPopup):
    model = ReportGraph
    form_class = ReportGraphForm
    permissions = 'reports'
    pk_url_kwarg = 'graph_id'
    title = _('Edit a graph for «{entity}»')


class GraphFetchingBase(base.CheckedView):
    # permissions = 'reports' => No, we want to get the "plot" even if the ReportGraph
    #                            cannot be seen (the plot's data use credentials any way).
    response_class = CremeJsonResponse
    chart_arg = 'chart'
    order_arg = 'order'
    save_settings_arg = 'save_settings'
    report_chart_registry = report_chart_registry

    def cast_chart(self, value):
        registry = self.report_chart_registry

        if value and not registry.get(value):
            raise ValueError('The "chart" argument is invalid : "{}" not in {}'.format(
                value,
                [c[0] for c in registry],
            ))

        return value

    def get(self, request, *args, **kwargs):
        chart = self.get_chart()
        order = self.get_order()
        save = self.get_save_settings()

        rgraph, x, y = self.get_graph_data(request=request, order=str(order))

        self.save_settings(
            rgraph=rgraph, chart=chart, asc=order.asc, save_settings=save,
        )

        # TODO: send error too ?
        return self.response_class({'x': x, 'y': y})

    def get_graph_data(self, request, order):
        raise NotImplementedError

    def get_chart(self):
        return utils.get_from_GET_or_404(
            self.request.GET,
            key=self.chart_arg,
            cast=self.cast_chart,
            default=None,
        )

    def get_order(self):
        return utils.get_from_GET_or_404(
            self.request.GET,
            key=self.order_arg,
            cast=Order.from_string,
            default='ASC',
        )

    def get_save_settings(self):
        return utils.get_from_GET_or_404(
            self.request.GET,
            key=self.save_settings_arg,
            cast=utils.bool_from_str_extended,
            default='0',
        )

    def save_settings(self, *, rgraph, chart, asc, save_settings):
        update_kw = {'asc': asc}

        if chart:
            update_kw['chart'] = chart

        if save_settings:
            if self.request.user.has_perm_to_change(rgraph):
                # TODO: does need we a 'default' chart value ??
                if (chart and chart != rgraph.chart) or asc != rgraph.asc:
                    type(rgraph).objects.filter(id=rgraph.id).update(**update_kw)
            else:
                logger.warning(
                    'The ReportGraph id="%s" cannot be edited, '
                    'so the settings are not saved.',
                    rgraph.id
                )


class GraphFetching(base.EntityRelatedMixin, GraphFetchingBase):
    entity_id_url_kwarg = 'graph_id'
    entity_classes = ReportGraph

    def check_related_entity_permissions(self, entity, user):
        # NB: we avoid the <user.has_perm_to_change_or_die(entity)> of super().
        #     (see GraphFetchingBase notes about credentials).
        pass

    def get_graph_data(self, request, order):
        rgraph = self.get_related_entity()
        x, y = rgraph.fetch(user=request.user, order=order)

        return rgraph, x, y


class GraphFetchingForInstance(base.EntityRelatedMixin, GraphFetchingBase):
    brick_item_id_url_kwarg = 'instance_brick_id'

    def __init__(self):
        super().__init__()
        self.instance_brick_item = None

    def get_instance_brick_item(self):
        brick_item = self.instance_brick_item

        if brick_item is None:
            self.instance_brick_item = brick_item = get_object_or_404(
                InstanceBrickConfigItem,
                pk=self.kwargs[self.brick_item_id_url_kwarg],
            )

        return brick_item

    def get_graph_data(self, request, order):
        brick_item = self.get_instance_brick_item()
        entity = self.get_related_entity()
        brick = brick_registry.get_brick_4_instance(brick_item, entity=entity)

        try:
            fetcher = brick.fetcher
        except AttributeError as e:
            raise ConflictError('Invalid brick: {e}') from e  # TODO: test

        try:
            x, y = fetcher.fetch_4_entity(
                entity=entity,
                order=order, user=request.user,
            )
        except (GraphFetcher.IncompatibleContentType, GraphFetcher.UselessResult):
            logger.exception(
                'Fetching error in %s.get_graph_data()',
                type(self).__name__,
            )
            x = y = None

        return fetcher.graph, x, y
