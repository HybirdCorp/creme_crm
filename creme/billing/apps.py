# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2021  Hybird
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

from django.core import checks
from django.utils.translation import gettext_lazy as _
from django.utils.translation import npgettext, pgettext

from creme.creme_core.apps import CremeAppConfig
from creme.creme_core.checks import Tags


class BillingConfig(CremeAppConfig):
    default = True
    name = 'creme.billing'
    verbose_name = _('Billing')
    dependencies = ['creme.persons', 'creme.products']

    def ready(self):
        # NB: it seems we cannot transform this a check_deps(self, **kwargs) method
        # because we get an error from django:
        # [AttributeError: 'instancemethod' object has no attribute 'tags']
        @checks.register(Tags.settings)
        def check_exporters(**kwargs):
            from .exporters import (
                BillingExportEngine,
                BillingExportEngineManager,
            )

            errors = []
            ids = set()

            for engine_cls in BillingExportEngineManager().engine_classes:
                if not issubclass(engine_cls, BillingExportEngine):
                    errors.append(
                        checks.Error(
                            f"the exporter engine {engine_cls} does not inherit "
                            f"<BillingExportEngine>.",
                            hint='Check the BILLING_EXPORTERS setting in your'
                                 ' local_settings.py/project_settings.py',
                            obj=self.name,
                            id='creme.billing.E001',
                        )
                    )

                if engine_cls.id in ids:
                    errors.append(
                        checks.Error(
                            f"the exporter {engine_cls} uses an id already used.",
                            hint='Check the BILLING_EXPORTERS setting in your'
                                 ' local_settings.py/project_settings.py',
                            obj=self.name,
                            id='creme.billing.E002',
                        )
                    )

                ids.add(engine_cls.id)

            return errors

    def all_apps_ready(self):
        from creme import billing

        self.CreditNote   = billing.get_credit_note_model()
        self.Invoice      = billing.get_invoice_model()
        self.Quote        = billing.get_quote_model()
        self.SalesOrder   = billing.get_sales_order_model()
        self.TemplateBase = billing.get_template_base_model()
        self.ProductLine  = billing.get_product_line_model()
        self.ServiceLine  = billing.get_service_line_model()
        super().all_apps_ready()

        self.register_billing_algorithm()
        self.register_billing_lines()

        from . import signals  # NOQA

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(
            self.Invoice,
            self.Quote,
            self.SalesOrder,
            self.CreditNote,
            self.ServiceLine,
            self.ProductLine,
        )

    def register_actions(self, actions_registry):
        from . import actions

        actions_registry.register_instance_actions(
            actions.ExportInvoiceAction,
            actions.ExportQuoteAction,
            actions.GenerateNumberAction,
        )

    def register_billing_algorithm(self):
        from .algos import SimpleAlgo
        from .models import SimpleBillingAlgo
        from .registry import algo_registry

        algo_registry.register((SimpleBillingAlgo.ALGO_NAME, SimpleAlgo))

    def register_billing_lines(self):
        from .registry import lines_registry
        lines_registry.register(self.ProductLine, self.ServiceLine)

    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(
            bricks.ProductLinesBrick,
            bricks.ServiceLinesBrick,
            bricks.CreditNotesBrick,
            bricks.TotalBrick,
            bricks.TargetBrick,
            bricks.ReceivedInvoicesBrick,
            bricks.PaymentInformationBrick,
            bricks.BillingPaymentInformationBrick,
            bricks.ReceivedQuotesBrick,
            bricks.ReceivedSalesOrdersBrick,
            bricks.ReceivedCreditNotesBrick,
            bricks.BillingDetailedAddressBrick,
            bricks.BillingPrettyAddressBrick,
            bricks.BillingExportersBrick,
            bricks.PersonsStatisticsBrick,
        ).register_invalid_models(
            self.ProductLine, self.ServiceLine,
        ).register_hat(
            self.CreditNote,   main_brick_cls=bricks.CreditNoteBarHatBrick,
        ).register_hat(
            self.Invoice,      main_brick_cls=bricks.InvoiceBarHatBrick
        ).register_hat(
            self.Quote,        main_brick_cls=bricks.QuoteBarHatBrick,
        ).register_hat(
            self.SalesOrder,   main_brick_cls=bricks.SalesOrderBarHatBrick,
        ).register_hat(
            self.TemplateBase, main_brick_cls=bricks.TemplateBaseBarHatBrick,
        )

    def register_bulk_update(self, bulk_update_registry):
        from .models import PaymentInformation

        register = bulk_update_registry.register
        register(self.ProductLine,   exclude=['on_the_fly_item'])
        register(self.ServiceLine,   exclude=['on_the_fly_item'])
        register(PaymentInformation, exclude=['organisation'])  # TODO: tags modifiable=False ??

    def register_buttons(self, button_registry):
        from . import buttons

        button_registry.register(
            buttons.GenerateInvoiceNumberButton,
            buttons.AddQuoteButton,
            buttons.AddSalesOrderButton,
            buttons.AddInvoiceButton,
            buttons.ConvertToInvoiceButton,
            buttons.ConvertToSalesOrderButton,
            buttons.ConvertToQuoteButton,
        )

    def register_creme_config(self, config_registry):
        from . import bricks, models

        register_model = config_registry.register_model
        register_model(models.InvoiceStatus,         'invoice_status')
        register_model(models.QuoteStatus,           'quote_status')
        register_model(models.CreditNoteStatus,      'credit_note_status')
        register_model(models.SalesOrderStatus,      'sales_order_status')
        register_model(models.AdditionalInformation, 'additional_information')
        register_model(models.PaymentTerms,          'payment_terms')
        register_model(models.SettlementTerms,       'invoice_payment_type')

        config_registry.register_app_bricks(
            'billing',
            bricks.BillingExportersBrick,
        )

    def register_custom_forms(self, cform_registry):
        from . import custom_forms

        cform_registry.register(
            custom_forms.INVOICE_CREATION_CFORM,
            custom_forms.INVOICE_EDITION_CFORM,

            custom_forms.QUOTE_CREATION_CFORM,
            custom_forms.QUOTE_EDITION_CFORM,

            custom_forms.ORDER_CREATION_CFORM,
            custom_forms.ORDER_EDITION_CFORM,

            custom_forms.CNOTE_CREATION_CFORM,
            custom_forms.CNOTE_EDITION_CFORM,

            custom_forms.BTEMPLATE_CREATION_CFORM,
            custom_forms.BTEMPLATE_EDITION_CFORM,
        )

    def register_fields_config(self, fields_config_registry):
        fields_config_registry.register_models(
            self.Invoice,
            self.Quote,
            self.SalesOrder,
            self.CreditNote,
            # TODO ?
            # self.ServiceLine,
            # self.ProductLine,
            # models.AdditionalInformation,
            # models.PaymentTerms,
            # models.PaymentInformation,
        )

    def register_field_printers(self, field_printers_registry):
        from .models.fields import BillingDiscountField
        from .utils import print_discount

        field_printers_registry.register(BillingDiscountField, print_discount)

    def register_function_fields(self, function_field_registry):
        from creme import persons

        from . import function_fields as ffields

        register = function_field_registry.register
        register(self.TemplateBase, ffields.TemplateBaseVerboseStatusField)

        for model in (persons.get_organisation_model(), persons.get_contact_model()):
            register(
                model,
                ffields._TotalPendingPayment,
                ffields._TotalWonQuoteThisYear,
                ffields._TotalWonQuoteLastYear,
            )

    def register_icons(self, icon_registry):
        icon_fmt = 'images/invoice_%(size)s.png'
        icon_registry.register(
            self.Invoice,      icon_fmt,
        ).register(
            self.Quote,        icon_fmt,
        ).register(
            self.SalesOrder,   icon_fmt,
        ).register(
            self.CreditNote,   icon_fmt,
        ).register(
            self.TemplateBase, icon_fmt,
        ).register(
            self.ProductLine,  icon_fmt,
        ).register(
            self.ServiceLine,  icon_fmt,
        )

    def register_mass_import(self, import_form_registry):
        from .forms.mass_import import get_import_form_builder

        import_form_registry.register(
            self.Invoice,    get_import_form_builder,
        ).register(
            self.Quote,      get_import_form_builder,
        ).register(
            self.SalesOrder, get_import_form_builder,
        )

    # def register_menu(self, creme_menu):
    #     CreditNote = self.CreditNote
    #     Invoice    = self.Invoice
    #     Quote      = self.Quote
    #     SalesOrder = self.SalesOrder
    #
    #     LvURLItem = creme_menu.URLItem.list_view
    #     creme_menu.get(
    #         'features',
    #     ).get_or_create(
    #         creme_menu.ContainerItem, 'management',
    #         priority=50,
    #         defaults={'label': _('Management')},
    #     ).add(
    #         LvURLItem('billing-quotes',        model=Quote),            priority=10,
    #     ).add(
    #         LvURLItem('billing-invoices',      model=Invoice),          priority=15,
    #     ).add(
    #         LvURLItem('billing-credit_notes',  model=CreditNote),       priority=50,
    #     ).add(
    #         LvURLItem('billing-sales_orders',  model=SalesOrder),       priority=55,
    #     ).add(
    #         LvURLItem('billing-product_lines', model=self.ProductLine), priority=200,
    #     ).add(
    #         LvURLItem('billing-service_lines', model=self.ServiceLine), priority=210,
    #     )
    #     creme_menu.get(
    #         'creation', 'any_forms',
    #     ).get_or_create_group(
    #         'management', _('Management'), priority=50,
    #     ).add_link(
    #         'billing-create_quote',   Quote,      priority=10,
    #     ).add_link(
    #         'billing-create_invoice', Invoice,    priority=15,
    #     ).add_link(
    #         'billing-create_cnote',   CreditNote, priority=50,
    #     ).add_link(
    #         'billing-create_order',   SalesOrder, priority=55,
    #     )

    def register_menu_entries(self, menu_registry):
        from . import menu

        menu_registry.register(
            menu.CreditNotesEntry,
            menu.InvoicesEntry,
            menu.QuotesEntry,
            menu.SalesOrdersEntry,
            menu.ProductLinesEntry,
            menu.ServiceLinesEntry,

            menu.CreditNoteCreationEntry,
            menu.InvoiceCreationEntry,
            menu.QuoteCreationEntry,
            menu.SalesOrderCreationEntry,
        )

    def register_creation_menu(self, creation_menu_registry):
        creation_menu_registry.get_or_create_group(
            'management', _('Management'), priority=50,
        ).add_link(
            'billing-create_quote',   self.Quote,      priority=10,
        ).add_link(
            'billing-create_invoice', self.Invoice,    priority=15,
        ).add_link(
            'billing-create_cnote',   self.CreditNote, priority=50,
        ).add_link(
            'billing-create_order',   self.SalesOrder, priority=55,
        )

    def register_setting_keys(self, setting_key_registry):
        from . import setting_keys

        setting_key_registry.register(
            setting_keys.payment_info_key,
            setting_keys.button_redirection_key,
        )

    def register_smart_columns(self, smart_columns_registry):
        from . import constants

        for model in (self.Invoice, self.Quote, self.SalesOrder, self.CreditNote):
            smart_columns_registry.register_model(
                model
            ).register_field(
                'number',
            ).register_field(
                'status',
            ).register_relationtype(constants.REL_SUB_BILL_RECEIVED)

    def register_statistics(self, statistics_registry):
        Invoice = self.Invoice
        Quote = self.Quote
        SalesOrder = self.SalesOrder

        def won_quotes():
            count = Quote.objects.filter(status__won=True).count()
            return npgettext(
                'billing-quote_stats',
                '{count} won',
                '{count} won',
                count
            ).format(count=count)

        statistics_registry.register(
            id='billing-invoices', label=Invoice._meta.verbose_name_plural,
            func=lambda: [Invoice.objects.count()],
            perm='billing', priority=20,
        ).register(
            id='billing-quotes', label=Quote._meta.verbose_name_plural,
            func=lambda: [
                won_quotes(),
                pgettext('billing-quote_stats', '{count} in all').format(
                    count=Quote.objects.count(),
                ),
            ],
            perm='billing', priority=22,
        ).register(
            id='billing-orders', label=SalesOrder._meta.verbose_name_plural,
            func=lambda: [SalesOrder.objects.count()],
            perm='billing', priority=24,
        )
