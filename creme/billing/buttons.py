# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.gui.button_menu import Button

from creme import persons

from .. import billing
from .constants import REL_OBJ_BILL_RECEIVED
from .models import Base


Invoice    = billing.get_invoice_model()
Quote      = billing.get_quote_model()
SalesOrder = billing.get_sales_order_model()


class GenerateInvoiceNumberButton(Button):
    id_           = Button.generate_id('billing', 'generate_invoice_number')
    verbose_name  = _('Generate the number of the Invoice')
    template_name = 'billing/buttons/generate-invoice-number.html'

    def get_ctypes(self):
        return (Invoice,)

    def has_perm(self, context):
        return context['user'].has_perm_to_change(context['object'])

    def ok_4_display(self, entity):
        return not bool(entity.number)


class _AddBillingDocumentButton(Button):
    template_name   = 'billing/buttons/add-billing-document.html'
    model_to_create = Base  # Overload
    url_name        = 'OVERLOADME'

    def get_ctypes(self):
        return persons.get_organisation_model(), persons.get_contact_model()

    def has_perm(self, context):
        return context['user'].has_perm_to_create(self.model_to_create)

    def render(self, context):
        context['verbose_name'] = self.verbose_name
        context['url_name'] = self.url_name

        meta = self.model_to_create._meta
        context['model_vname'] = meta.verbose_name
        context['model_id'] = '{}.{}'.format(meta.app_label, meta.model_name)

        context['rtype_id'] = REL_OBJ_BILL_RECEIVED

        return super().render(context)


class AddInvoiceButton(_AddBillingDocumentButton):
    model_to_create = Invoice
    id_          = Button.generate_id('billing', 'add_invoice')
    verbose_name = _('Create a related invoice')
    permission   = cperm(Invoice)
    url_name     = 'billing__create_related_invoice'


class AddSalesOrderButton(_AddBillingDocumentButton):
    model_to_create = SalesOrder
    id_             = Button.generate_id('billing', 'add_salesorder')
    verbose_name    = _('Create a related salesorder')
    permission      = cperm(SalesOrder)
    url_name        = 'billing__create_related_order'


class AddQuoteButton(_AddBillingDocumentButton):
    model_to_create = Quote
    id_             = Button.generate_id('billing', 'add_quote')
    verbose_name    = _('Create a related quote')
    permission      = cperm(Quote)
    url_name        = 'billing__create_related_quote'

