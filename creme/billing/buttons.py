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

from creme import persons
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.gui.button_menu import Button
from creme.creme_core.models import SettingValue

from .. import billing
from .constants import REL_OBJ_BILL_RECEIVED
from .core import BILLING_MODELS, conversion
from .core.number_generation import number_generator_registry
from .models import Base, NumberGeneratorItem
from .setting_keys import button_redirection_key

CreditNote = billing.get_credit_note_model()
Invoice    = billing.get_invoice_model()
Quote      = billing.get_quote_model()
SalesOrder = billing.get_sales_order_model()


class GenerateNumberButton(Button):
    id = Button.generate_id('billing', 'generate_number')
    verbose_name = _('Generate the number')
    description = _(
        'This button generates the number for the current Invoice/Credit Note.\n'
        'App: Billing'
    )
    dependencies = (Button.CURRENT,)
    template_name = 'billing/buttons/generate-number.html'

    generator_registry = number_generator_registry

    def get_ctypes(self):
        return [
            model for model in BILLING_MODELS if not model.generate_number_in_create
        ]

    def check_permissions(self, *, entity, request):
        super().check_permissions(entity=entity, request=request)

        item = NumberGeneratorItem.objects.get_for_instance(entity)
        if item is None:
            raise ConflictError(_(
                'This entity cannot generate a number '
                '(see configuration of the app Billing)'
            ))

        self.generator_registry[item].check_permissions(
            user=request.user, entity=entity,
        )

    # def ok_4_display(self, entity):
    def is_displayed(self, *, entity, request):
        return not entity.generate_number_in_create


class _AddBillingDocumentButton(Button):
    # dependencies = [Relation]  # TODO: see billing-action.js (reloading is manually managed)
    template_name = 'billing/buttons/add-billing-document.html'
    model_to_create = Base  # Override

    url_name = 'OVERRIDE_ME'

    def check_permissions(self, *, entity, request):
        super().check_permissions(entity=entity, request=request)

        user = request.user
        user.has_perm_to_create_or_die(self.model_to_create)
        user.has_perm_to_link_or_die(entity)

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


class AddInvoiceButton(_AddBillingDocumentButton):
    model_to_create = Invoice
    id = Button.generate_id('billing', 'add_invoice')
    verbose_name = _('Create a related invoice')
    description = _(
        'This button displays the creation form for invoices. '
        'The current entity is pre-selected to be the target of the created invoice.\n'
        'App: Billing'
    )
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
    url_name = 'billing__create_related_quote'


class _ConvertToButton(Button):
    template_name = 'billing/buttons/convert-to.html'
    target_model = Base  # Override
    converter_registry = conversion.converter_registry

    def _target_name(self):
        from .views.conversion import Conversion

        target_model = self.target_model
        for model_name, model_cls in Conversion.target_models.items():
            if target_model == model_cls:
                return model_name

        return 'INVALID'

    def check_permissions(self, *, entity, request):
        super().check_permissions(entity=entity, request=request)

        converter = self.converter_registry.get_converter(
            user=request.user, source=entity, target_model=self.target_model,
        )
        if converter is None:
            raise ConflictError(_(
                'This conversion has been removed; you should remove this button.'
            ))

        converter.check_permissions()

    def get_context(self, *, entity, request):
        context = super().get_context(entity=entity, request=request)
        context['convert_to'] = self._target_name()
        context['model_vname'] = self.target_model._meta.verbose_name

        return context

    def get_ctypes(self):
        current_target = self.target_model

        return [
            source
            for source, target in self.converter_registry.models
            if target == current_target
        ]


class ConvertToInvoiceButton(_ConvertToButton):
    id = Button.generate_id('billing', 'convert_to_invoice')
    verbose_name = _('Convert to Invoice')
    description = _(
        'This button converts automatically the current entity into an invoice. '
        'Notice that the current entity is kept unchanged, a new invoice is created.\n'
        'App: Billing'
    )
    target_model = Invoice


class ConvertToSalesOrderButton(_ConvertToButton):
    id = Button.generate_id('billing', 'convert_to_salesorder')
    verbose_name = _('Convert to Salesorder')
    description = _(
        'This button converts automatically the current entity into an salesorder. '
        'Notice that the current entity is kept unchanged, a new order is created.\n'
        'App: Billing'
    )
    target_model = SalesOrder


class ConvertToQuoteButton(_ConvertToButton):
    id = Button.generate_id('billing', 'convert_to_quote')
    verbose_name = _('Convert to Quote')
    description = _(
        'This button converts automatically the current entity into an quote. '
        'Notice that the current entity is kept unchanged, a new quote is created.\n'
        'App: Billing'
    )
    target_model = Quote
