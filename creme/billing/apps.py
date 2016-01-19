# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015  Hybird
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

from creme.creme_core.apps import CremeAppConfig


class BillingConfig(CremeAppConfig):
    name = 'creme.billing'
    verbose_name = _(u'Billing')
    dependencies = ['creme.persons', 'creme.products']

#    def ready(self):
    def all_apps_ready(self):
        from . import (get_credit_note_model, get_invoice_model, get_quote_model,
                get_sales_order_model, get_template_base_model,
                get_product_line_model, get_service_line_model)

        self.CreditNote   = get_credit_note_model()
        self.Invoice      = get_invoice_model()
        self.Quote        = get_quote_model()
        self.SalesOrder   = get_sales_order_model()
        self.TemplateBase = get_template_base_model()
        self.ProductLine  = get_product_line_model()
        self.ServiceLine  = get_service_line_model()
#        super(BillingConfig, self).ready()
        super(BillingConfig, self).all_apps_ready()

        from . import signals
        from .function_fields import hook_organisation

        hook_organisation()

    def register_creme_app(self, creme_registry):
        creme_registry.register_app('billing', _(u'Billing'), '/billing')

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.Invoice, self.Quote,
                                              self.SalesOrder, self.CreditNote,
                                              self.ServiceLine, self.ProductLine,
                                             )

    def register_blocks(self, block_registry):
        from .blocks import block_list # BillingBlock

        block_registry.register(*block_list)
        block_registry.register_invalid_models(self.ProductLine, self.ServiceLine)

    def register_bulk_update(self, bulk_update_registry):
        from .models import PaymentInformation

        register = bulk_update_registry.register
        register(self.ProductLine,   exclude=['on_the_fly_item'])
        register(self.ServiceLine,   exclude=['on_the_fly_item'])
        register(PaymentInformation, exclude=['organisation']) # TODO: tags modifiable=False ??

    def register_buttons(self, button_registry):
        from .buttons import button_list

        button_registry.register(*button_list)

    def register_field_printers(self, field_printers_registry):
        from .models.fields  import BillingDiscountField

        from .utils import print_discount

        field_printers_registry.register(BillingDiscountField, print_discount)

    def register_icons(self, icon_registry):
        reg_icon = icon_registry.register
        icon_fmt = 'images/invoice_%(size)s.png'
        reg_icon(self.Invoice,      icon_fmt)
        reg_icon(self.Quote,        icon_fmt)
        reg_icon(self.SalesOrder,   icon_fmt)
        reg_icon(self.CreditNote,   icon_fmt)
        reg_icon(self.TemplateBase, icon_fmt)
        reg_icon(self.ProductLine,  icon_fmt)
        reg_icon(self.ServiceLine,  icon_fmt)

    def register_mass_import(self, import_form_registry):
        from .forms.lv_import import get_import_form_builder

        reg_import_form = import_form_registry.register
        reg_import_form(self.Invoice,    get_import_form_builder)
        reg_import_form(self.Quote,      get_import_form_builder)
        reg_import_form(self.SalesOrder, get_import_form_builder)

    def register_menu(self, creme_menu):
        from django.core.urlresolvers import reverse_lazy as reverse

        from creme.creme_core.auth import build_creation_perm as cperm

        CreditNote   = self.CreditNote
        Invoice      = self.Invoice
        Quote        = self.Quote
        SalesOrder   = self.SalesOrder
        reg_item = creme_menu.register_app('billing', '/billing/').register_item
        reg_item('/billing/',                            _(u'Portal of billing'),   'billing')
        reg_item(reverse('billing__create_invoice'),     Invoice.creation_label,    cperm(Invoice))
        reg_item(reverse('billing__list_invoices'),      _(u'All invoices'),        'billing')
        reg_item(reverse('billing__create_order'),       SalesOrder.creation_label, cperm(SalesOrder))
        reg_item(reverse('billing__list_orders'),        _(u'All sales orders'),    'billing')
        reg_item(reverse('billing__create_quote'),       Quote.creation_label,      cperm(Quote))
        reg_item(reverse('billing__list_quotes'),        _(u'All quotes'),          'billing')
        reg_item(reverse('billing__create_cnote'),       CreditNote.creation_label, cperm(CreditNote))
        reg_item(reverse('billing__list_cnotes'),        _(u'All credit notes'),    'billing')
        reg_item(reverse('billing__list_product_lines'), _(u'All product lines'),   'billing')
        reg_item(reverse('billing__list_service_lines'), _(u'All service lines'),   'billing')

    def register_setting_key(self, setting_key_registry):
        from .setting_keys import payment_info_key

        setting_key_registry.register(payment_info_key)

    def register_smart_columns(self, smart_columns_registry):
        from .constants import REL_SUB_BILL_RECEIVED

        for model in (self.Invoice, self.Quote, self.SalesOrder, self.CreditNote):
            smart_columns_registry.register_model(model) \
                                  .register_field('number') \
                                  .register_field('status') \
                                  .register_relationtype(REL_SUB_BILL_RECEIVED)
