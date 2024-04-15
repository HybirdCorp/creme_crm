################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2024  Hybird
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
    id = Button.generate_id('billing', 'generate_invoice_number')
    verbose_name = _('Generate the number of the Invoice')
    description = _(
        'This button generates the number for the current invoice.\n'
        'App: Billing'
    )
    dependencies = [Invoice]
    template_name = 'billing/buttons/generate-invoice-number.html'

    def get_ctypes(self):
        return (Invoice,)

    def is_allowed(self, *, entity, request):
        return super().is_allowed(
            entity=entity, request=request,
        ) and request.user.has_perm_to_change(entity)

    def ok_4_display(self, entity):
        return not bool(entity.number)


class _AddBillingDocumentButton(Button):
    # dependencies = [Relation]  # TODO: see billing-action.js (reloading is manually managed)
    template_name = 'billing/buttons/add-billing-document.html'
    model_to_create = Base  # Override

    url_name = 'OVERRIDE_ME'

    def get_context(self, *, entity, request):
        context = super().get_context(entity=entity, request=request)
        context['url_name'] = self.url_name

        # TODO: pass only "_meta" to the template?
        meta = self.model_to_create._meta
        context['model_vname'] = str(meta.verbose_name)
        context['model_id'] = f'{meta.app_label}.{meta.model_name}'

        context['rtype_id'] = REL_OBJ_BILL_RECEIVED

        context['redirect'] = SettingValue.objects.get_4_key(
            button_redirection_key,
            default=True,
        ).value

        return context

    def get_ctypes(self):
        return persons.get_organisation_model(), persons.get_contact_model()

    def is_allowed(self, *, entity, request):
        return (
            super().is_allowed(entity=entity, request=request)
            and request.user.has_perm_to_create(self.model_to_create)
        )


class AddInvoiceButton(_AddBillingDocumentButton):
    model_to_create = Invoice
    id = Button.generate_id('billing', 'add_invoice')
    verbose_name = _('Create a related invoice')
    description = _(
        'This button displays the creation form for invoices. '
        'The current entity is pre-selected to be the target of the created invoice.\n'
        'App: Billing'
    )
    permissions = cperm(Invoice)
    url_name = 'billing__create_related_invoice'


class AddSalesOrderButton(_AddBillingDocumentButton):
    model_to_create = SalesOrder
    id = Button.generate_id('billing', 'add_salesorder')
    verbose_name = _('Create a related salesorder')
    description = _(
        'This button displays the creation form for salesorders. '
        'The current entity is pre-selected to be the target of the created order.\n'
        'App: Billing'
    )
    permissions = cperm(SalesOrder)
    url_name = 'billing__create_related_order'


class AddQuoteButton(_AddBillingDocumentButton):
    model_to_create = Quote
    id = Button.generate_id('billing', 'add_quote')
    verbose_name = _('Create a related quote')
    description = _(
        'This button displays the creation form for quotes. '
        'The current entity is pre-selected to be the target of the created quote.\n'
        'App: Billing'
    )
    permissions = cperm(Quote)
    url_name = 'billing__create_related_quote'


class _ConvertToButton(Button):
    template_name = 'billing/buttons/convert-to.html'
    target_model = Base  # Override
    target_modelname = ''  # Override

    def get_context(self, *, entity, request):
        context = super().get_context(entity=entity, request=request)
        context['convert_to'] = self.target_modelname

        target_model = self.target_model
        context['model_vname'] = target_model._meta.verbose_name
        context['creation_perm'] = request.user.has_perm_to_create(target_model)

        return context

    def get_ctypes(self):
        return tuple(get_models_for_conversion(self.target_modelname))

    def is_allowed(self, *, entity, request):
        user = request.user
        return (
            super().is_allowed(entity=entity, request=request)
            and not user.is_staff
            and not entity.is_deleted
        )


class ConvertToInvoiceButton(_ConvertToButton):
    id = Button.generate_id('billing', 'convert_to_invoice')
    verbose_name = _('Convert to Invoice')
    description = _(
        'This button converts automatically the current entity into an invoice. '
        'Notice that the current entity is kept unchanged, a new invoice is created.\n'
        'App: Billing'
    )
    target_model = Invoice
    target_modelname = 'invoice'


class ConvertToSalesOrderButton(_ConvertToButton):
    id = Button.generate_id('billing', 'convert_to_salesorder')
    verbose_name = _('Convert to Salesorder')
    description = _(
        'This button converts automatically the current entity into an salesorder. '
        'Notice that the current entity is kept unchanged, a new order is created.\n'
        'App: Billing'
    )
    target_model = SalesOrder
    target_modelname = 'sales_order'


class ConvertToQuoteButton(_ConvertToButton):
    id = Button.generate_id('billing', 'convert_to_quote')
    verbose_name = _('Convert to Quote')
    description = _(
        'This button converts automatically the current entity into an quote. '
        'Notice that the current entity is kept unchanged, a new quote is created.\n'
        'App: Billing'
    )
    target_model = Quote
    target_modelname = 'quote'
