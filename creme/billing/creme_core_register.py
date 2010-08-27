# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.utils.translation import ugettext_lazy as _

from creme_core.registry import creme_registry
from creme_core.gui.menu import creme_menu
from creme_core.gui.block import block_registry

from billing.models import Invoice, Quote, SalesOrder, CreditNote
from billing.blocks import product_lines_block, service_lines_block, total_block


creme_registry.register_app('billing', _(u'Billing'), '/billing')
creme_registry.register_entity_models(Invoice, Quote, SalesOrder, CreditNote)

creme_menu.register_app('billing', '/billing/', 'Facturation') #TODO: i18n
reg_menu = creme_menu.register_menu
reg_menu('billing', '/billing/',                _(u'Portal'))
reg_menu('billing', '/billing/invoice/add',     _(u'Add an invoice'))
reg_menu('billing', '/billing/invoices',        _(u'All invoices'))
reg_menu('billing', '/billing/sales_order/add', _(u'Add a sales order'))
reg_menu('billing', '/billing/sales_orders',    _(u'All sales orders'))
reg_menu('billing', '/billing/quote/add',       _(u'Add a quote'))
reg_menu('billing', '/billing/quotes',          _(u'All quotes'))
reg_menu('billing', '/billing/credit_note/add', _(u'Add a credit note'))
reg_menu('billing', '/billing/credit_note',     _(u'All credit notes'))

block_registry.register(product_lines_block, service_lines_block, total_block)
