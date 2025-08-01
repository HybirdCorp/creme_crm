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

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.views import generic

from ... import billing
from .. import custom_forms
from ..constants import DEFAULT_HFILTER_ORDER
from . import base

SalesOrder = billing.get_sales_order_model()
Invoice = billing.get_invoice_model()


class SalesOrderCreation(generic.EntityCreation):
    model = SalesOrder
    form_class = custom_forms.ORDER_CREATION_CFORM


class RelatedSalesOrderCreation(base.RelatedBaseCreation):
    model = SalesOrder
    form_class = custom_forms.ORDER_CREATION_CFORM
    permissions = ('billing', cperm(SalesOrder))
    title = _('Create a salesorder for «{entity}»')


class SalesOrderDetail(generic.EntityDetail):
    model = SalesOrder
    template_name = 'billing/view_sales_order.html'
    pk_url_kwarg = 'order_id'


class SalesOrderEdition(generic.EntityEdition):
    model = SalesOrder
    form_class = custom_forms.ORDER_EDITION_CFORM
    pk_url_kwarg = 'order_id'


class SalesOrdersList(base.BaseList):
    model = SalesOrder
    default_headerfilter_id = DEFAULT_HFILTER_ORDER
