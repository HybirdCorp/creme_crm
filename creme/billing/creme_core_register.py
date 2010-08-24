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


creme_registry.register_app('billing', _(u'Facturation'), '/billing')
creme_registry.register_entity_models(Invoice, Quote, SalesOrder, CreditNote)

creme_menu.register_app ('billing', '/billing/', 'Facturation')
reg_menu = creme_menu.register_menu
reg_menu('billing', '/billing/invoice/add',     'Ajouter une facture')
reg_menu('billing', '/billing/invoices',        'Lister les factures')
reg_menu('billing', '/billing/sales_order/add', 'Ajouter un bon de commande')
reg_menu('billing', '/billing/sales_orders',    'Lister les bons de commande')
reg_menu('billing', '/billing/quote/add',       'Ajouter un devis')
reg_menu('billing', '/billing/quotes',          'Lister les devis')
reg_menu('billing', '/billing/credit_note/add',       'Ajouter un avoir')
reg_menu('billing', '/billing/credit_note',          'Lister les avoirs')

block_registry.register(product_lines_block, service_lines_block, total_block)
