# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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
from creme_core.gui import creme_menu, button_registry, block_registry, icon_registry, bulk_update_registry

from billing.models import Invoice, Quote, SalesOrder, CreditNote, Base, TemplateBase, Line, ServiceLine, ProductLine
from billing.blocks import block_list
from billing.buttons import generate_invoice_number_button


creme_registry.register_app('billing', _(u'Billing'), '/billing')
creme_registry.register_entity_models(Invoice, Quote, SalesOrder, CreditNote, Line, ServiceLine, ProductLine)

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
reg_item('/billing/lines',           _(u'All lines'),         'billing')
reg_item('/billing/product_lines',   _(u'All product lines'), 'billing')
reg_item('/billing/service_lines',   _(u'All service lines'), 'billing')

block_registry.register(*block_list)
button_registry.register(generate_invoice_number_button)

reg_icon = icon_registry.register
reg_icon(Invoice,      'images/invoice_%(size)s.png')
reg_icon(Quote,        'images/invoice_%(size)s.png')
reg_icon(SalesOrder,   'images/invoice_%(size)s.png')
reg_icon(CreditNote,   'images/invoice_%(size)s.png')
reg_icon(TemplateBase, 'images/invoice_%(size)s.png')

from signals import connect_to_signals

connect_to_signals()

bulk_update_registry.register(
    (Base,         ['number', 'total_vat', 'total_no_vat', 'payment_info']),
    (CreditNote,   ['status']),
    (Invoice,      ['status']),
    (Quote,        ['status']),
    (SalesOrder,   ['status']),
    (TemplateBase, ['status_id', 'ct', 'base_ptr']),
)
