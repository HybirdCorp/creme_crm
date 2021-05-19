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

from django.utils.translation import gettext_lazy as _

from creme import persons
from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.gui.button_menu import Button
from creme.creme_core.models import SettingValue

from .. import billing
from .constants import REL_OBJ_BILL_RECEIVED
from .core import get_models_for_conversion
from .models import Base
from .setting_keys import button_redirection_key

Invoice    = billing.get_invoice_model()
Quote      = billing.get_quote_model()
SalesOrder = billing.get_sales_order_model()


class GenerateInvoiceNumberButton(Button):
    id_ = Button.generate_id('billing', 'generate_invoice_number')
    verbose_name = _('Generate the number of the Invoice')
    description = _(
        'This button generates the number for the current invoice.\n'
        'App: Billing'
    )
    template_name = 'billing/buttons/generate-invoice-number.html'

    def get_ctypes(self):
        return (Invoice,)

    def has_perm(self, context):
        return context['user'].has_perm_to_change(context['object'])

    def ok_4_display(self, entity):
        return not bool(entity.number)


class _AddBillingDocumentButton(Button):
    template_name = 'billing/buttons/add-billing-document.html'
    model_to_create = Base  # Overload

    url_name = 'OVERLOADME'

    def get_ctypes(self):
        return persons.get_organisation_model(), persons.get_contact_model()

    def has_perm(self, context):
        return context['user'].has_perm_to_create(self.model_to_create)

    def render(self, context):
        context['verbose_name'] = self.verbose_name
        context['url_name'] = self.url_name

        meta = self.model_to_create._meta
        context['model_vname'] = meta.verbose_name
        context['model_id'] = f'{meta.app_label}.{meta.model_name}'

        context['rtype_id'] = REL_OBJ_BILL_RECEIVED

        context['redirect'] = SettingValue.objects.get_4_key(
            button_redirection_key,
            default=True,
        ).value

        return super().render(context)


class AddInvoiceButton(_AddBillingDocumentButton):
    model_to_create = Invoice
    id_ = Button.generate_id('billing', 'add_invoice')
    verbose_name = _('Create a related invoice')
    description = _(
        'This button displays the creation form for invoices. '
        'The current entity is pre-selected to be the target of the created invoice.\n'
        'App: Billing'
    )
    # permission = cperm(Invoice)
    permissions = cperm(Invoice)
    url_name = 'billing__create_related_invoice'


class AddSalesOrderButton(_AddBillingDocumentButton):
    model_to_create = SalesOrder
    id_ = Button.generate_id('billing', 'add_salesorder')
    verbose_name = _('Create a related salesorder')
    description = _(
        'This button displays the creation form for salesorders. '
        'The current entity is pre-selected to be the target of the created order.\n'
        'App: Billing'
    )
    # permission = cperm(SalesOrder)
    permissions = cperm(SalesOrder)
    url_name = 'billing__create_related_order'


class AddQuoteButton(_AddBillingDocumentButton):
    model_to_create = Quote
    id_ = Button.generate_id('billing', 'add_quote')
    verbose_name = _('Create a related quote')
    description = _(
        'This button displays the creation form for quotes. '
        'The current entity is pre-selected to be the target of the created quote.\n'
        'App: Billing'
    )
    # permission = cperm(Quote)
    permissions = cperm(Quote)
    url_name = 'billing__create_related_quote'


class _ConvertToButton(Button):
    template_name = 'billing/buttons/convert-to.html'
    target_model = Base  # Overload
    target_modelname = ''

    def get_ctypes(self):
        return tuple(get_models_for_conversion(self.target_modelname))

    def has_perm(self, context):
        user = context['user']
        return (
            user.has_perm_to_create(self.target_model)
            and not user.is_staff
            and not context['object'].is_deleted
        )

    def render(self, context):
        context['verbose_name'] = self.verbose_name
        context['convert_to'] = self.target_modelname

        return super().render(context)


class ConvertToInvoiceButton(_ConvertToButton):
    id_ = Button.generate_id('billing', 'convert_to_invoice')
    verbose_name = _('Convert to Invoice')
    description = _(
        'This button converts automatically the current entity into an invoice. '
        'Notice that the current entity is kept unchanged, a new invoice is created.\n'
        'App: Billing'
    )
    target_model = Invoice
    target_modelname = 'invoice'


class ConvertToSalesOrderButton(_ConvertToButton):
    id_ = Button.generate_id('billing', 'convert_to_salesorder')
    verbose_name = _('Convert to Salesorder')
    description = _(
        'This button converts automatically the current entity into an salesorder. '
        'Notice that the current entity is kept unchanged, a new order is created.\n'
        'App: Billing'
    )
    target_model = SalesOrder
    target_modelname = 'sales_order'


class ConvertToQuoteButton(_ConvertToButton):
    id_ = Button.generate_id('billing', 'convert_to_quote')
    verbose_name = _('Convert to Quote')
    description = _(
        'This button converts automatically the current entity into an quote. '
        'Notice that the current entity is kept unchanged, a new quote is created.\n'
        'App: Billing'
    )
    target_model = Quote
    target_modelname = 'quote'
