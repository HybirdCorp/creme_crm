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
from creme_core.gui.button_menu import button_registry
from creme_core.gui.block import block_registry

from billing.models import Invoice, Quote, SalesOrder, CreditNote
from billing.blocks import product_lines_block, service_lines_block, total_block
from billing.buttons import generate_invoice_number_button


creme_registry.register_app('billing', _(u'Billing'), '/billing')
creme_registry.register_entity_models(Invoice, Quote, SalesOrder, CreditNote)

reg_item = creme_menu.register_app('billing', '/billing/').register_item
reg_item('/billing/',                _(u'Portal'),            'billing')
reg_item('/billing/invoice/add',     _(u'Add an invoice'),    'billing.add_invoice')
reg_item('/billing/invoices',        _(u'All invoices'),      'billing')
reg_item('/billing/sales_order/add', _(u'Add a sales order'), 'billing.add_salesorder')
reg_item('/billing/sales_orders',    _(u'All sales orders'),  'billing')
reg_item('/billing/quote/add',       _(u'Add a quote'),       'billing.add_quote')
reg_item('/billing/quotes',          _(u'All quotes'),        'billing')
reg_item('/billing/credit_note/add', _(u'Add a credit note'), 'billing.add_creditnote')
reg_item('/billing/credit_note',     _(u'All credit notes'),  'billing')

block_registry.register(product_lines_block, service_lines_block, total_block)
button_registry.register(generate_invoice_number_button)

from signals import connect_to_signals

connect_to_signals ()