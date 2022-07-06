################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2021  Hybird
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

from creme import billing
from creme.creme_core.gui import menu

CreditNote = billing.get_credit_note_model()
Invoice = billing.get_invoice_model()
Quote = billing.get_quote_model()
SalesOrder = billing.get_sales_order_model()
# TODO: TemplateBase list-view ?


class CreditNotesEntry(menu.ListviewEntry):
    id = 'billing-credit_notes'
    model = CreditNote


class InvoicesEntry(menu.ListviewEntry):
    id = 'billing-invoices'
    model = Invoice


class QuotesEntry(menu.ListviewEntry):
    id = 'billing-quotes'
    model = Quote


class SalesOrdersEntry(menu.ListviewEntry):
    id = 'billing-sales_orders'
    model = SalesOrder


class ProductLinesEntry(menu.ListviewEntry):
    id = 'billing-product_lines'
    model = billing.get_product_line_model()


class ServiceLinesEntry(menu.ListviewEntry):
    id = 'billing-service_lines'
    model = billing.get_service_line_model()


class CreditNoteCreationEntry(menu.CreationEntry):
    id = 'billing-create_credit_note'
    model = CreditNote


class InvoiceCreationEntry(menu.CreationEntry):
    id = 'billing-create_invoice'
    model = Invoice


class QuoteCreationEntry(menu.CreationEntry):
    id = 'billing-create_quote'
    model = Quote


class SalesOrderCreationEntry(menu.CreationEntry):
    id = 'billing-create_sales_order'
    model = SalesOrder
