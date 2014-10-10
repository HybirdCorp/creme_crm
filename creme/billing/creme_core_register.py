# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from creme.creme_core.core.setting_key import setting_key_registry
from creme.creme_core.registry import creme_registry
from creme.creme_core.gui import (creme_menu, button_registry, block_registry,
        icon_registry, import_form_registry, bulk_update_registry, smart_columns_registry)

from .blocks import block_list, BillingBlock
from .buttons import button_list
from .constants import REL_SUB_BILL_RECEIVED
from .function_fields import hook_organisation
from .forms.lv_import import get_import_form_builder
from .models import (Invoice, Quote, SalesOrder, CreditNote, TemplateBase,
        Line, ServiceLine, ProductLine) #Base
from .setting_keys import payment_info_key


creme_registry.register_app('billing', _(u'Billing'), '/billing')
creme_registry.register_entity_models(Invoice, Quote, SalesOrder, CreditNote, Line, ServiceLine, ProductLine)

reg_item = creme_menu.register_app('billing', '/billing/').register_item
reg_item('/billing/',                _(u'Portal of billing'),   'billing')
reg_item('/billing/invoice/add',     Invoice.creation_label,    'billing.add_invoice')
reg_item('/billing/invoices',        _(u'All invoices'),        'billing')
reg_item('/billing/sales_order/add', SalesOrder.creation_label, 'billing.add_salesorder')
reg_item('/billing/sales_orders',    _(u'All sales orders'),    'billing')
reg_item('/billing/quote/add',       Quote.creation_label,      'billing.add_quote')
reg_item('/billing/quotes',          _(u'All quotes'),          'billing')
reg_item('/billing/credit_note/add', CreditNote.creation_label, 'billing.add_creditnote')
reg_item('/billing/credit_note',     _(u'All credit notes'),    'billing')
reg_item('/billing/lines',           _(u'All lines'),           'billing')
reg_item('/billing/product_lines',   _(u'All product lines'),   'billing')
reg_item('/billing/service_lines',   _(u'All service lines'),   'billing')

block_registry.register_4_model(Quote,        BillingBlock())
block_registry.register_4_model(Invoice,      BillingBlock())
block_registry.register_4_model(SalesOrder,   BillingBlock())
block_registry.register_4_model(TemplateBase, BillingBlock())

block_registry.register(*block_list)
button_registry.register(*button_list)

reg_icon = icon_registry.register
reg_icon(Invoice,      'images/invoice_%(size)s.png')
reg_icon(Quote,        'images/invoice_%(size)s.png')
reg_icon(SalesOrder,   'images/invoice_%(size)s.png')
reg_icon(CreditNote,   'images/invoice_%(size)s.png')
reg_icon(TemplateBase, 'images/invoice_%(size)s.png')
reg_icon(ProductLine,  'images/invoice_%(size)s.png')
reg_icon(ServiceLine,  'images/invoice_%(size)s.png')

reg_import_form = import_form_registry.register
reg_import_form(Invoice,    get_import_form_builder)
reg_import_form(Quote,      get_import_form_builder)
reg_import_form(SalesOrder, get_import_form_builder)

bulk_update_registry.register(TemplateBase, exclude=['status_id', 'ct', 'base_ptr'])

setting_key_registry.register(payment_info_key)


for model in (Invoice, Quote, SalesOrder, CreditNote):
    smart_columns_registry.register_model(model) \
                          .register_field('number') \
                          .register_field('status') \
                          .register_relationtype(REL_SUB_BILL_RECEIVED)

hook_organisation()
