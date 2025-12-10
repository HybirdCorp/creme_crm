################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2025  Hybird
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

        self.register_billing_number_generators()
        self.register_billing_converters()
        self.register_billing_lines()
        self.register_billing_spawners()

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

    def register_actions(self, action_registry):
        from . import actions

        action_registry.register_instance_actions(
            actions.ExportInvoiceAction,
            actions.ExportQuoteAction,
            actions.GenerateInvoiceNumberAction,
            actions.GenerateCreditNoteNumberAction,
        ).register_bulk_actions(
            actions.BulkExportInvoiceAction,
            actions.BulkExportQuoteAction,
        )

    def register_aggregators(self, aggregator_registry):
        for model in [self.Invoice, self.Quote, self.SalesOrder, self.CreditNote]:
            aggregator_registry.model(model).add_aggregator(
                field='total_vat', label='Σ', function='Sum',
            ).add_aggregator(
                field='total_vat', label='μ', function='Avg',
            ).add_aggregator(
                field='total_no_vat', label='Σ', function='Sum',
            ).add_aggregator(
                field='total_no_vat', label='μ', function='Avg',
            )

    def register_billing_number_generators(self):
        from . import number_generators
        from .core.number_generation import number_generator_registry

        number_generator_registry.register(
            model=self.Invoice,
            generator_cls=number_generators.InvoiceRegularNumberGenerator,
        ).register(
            model=self.Quote,
            generator_cls=number_generators.QuoteRegularNumberGenerator,
        ).register(
            model=self.SalesOrder,
            generator_cls=number_generators.SalesOrderRegularNumberGenerator,
        ).register(
            model=self.CreditNote,
            generator_cls=number_generators.CreditNoteRegularNumberGenerator,
        )

    def register_billing_converters(self):
        from . import converters
        from .core import conversion

        conversion.converter_registry.register(
            source_model=self.Invoice,
            target_model=self.Quote,
            converter_class=converters.InvoiceToQuoteConverter,
        ).register(
            source_model=self.Quote,
            target_model=self.SalesOrder,
            converter_class=converters.QuoteToSalesOrderConverter,
        ).register(
            source_model=self.Quote,
            target_model=self.Invoice,
            converter_class=converters.QuoteToInvoiceConverter,
        ).register(
            source_model=self.SalesOrder,
            target_model=self.Invoice,
            converter_class=converters.SalesOrderToInvoiceConverter,
        )

    def register_billing_lines(self):
        from .core import line
        line.line_registry.register(self.ProductLine, self.ServiceLine)

    def register_billing_spawners(self):
        from . import spawners
        from .core import spawning

        spawning.spawner_registry.register(
            model=self.Invoice, cloner_class=spawners.InvoiceSpawner,
        ).register(
            model=self.Quote, cloner_class=spawners.QuoteSpawner,
        ).register(
            model=self.SalesOrder, cloner_class=spawners.SalesOrderSpawner,
        ).register(
            model=self.CreditNote, cloner_class=spawners.CreditNoteSpawner,
        )

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
            bricks.PersonsStatisticsBrick,
        ).register_invalid_models(
            self.ProductLine, self.ServiceLine,
        ).register_hat(
            self.CreditNote,
            main_brick_cls=bricks.CreditNoteBarHatBrick,
            secondary_brick_classes=[bricks.CreditNoteCardHatBrick],
        ).register_hat(
            self.Invoice,
            main_brick_cls=bricks.InvoiceBarHatBrick,
            secondary_brick_classes=[bricks.InvoiceCardHatBrick],
        ).register_hat(
            self.Quote,
            main_brick_cls=bricks.QuoteBarHatBrick,
            secondary_brick_classes=[bricks.QuoteCardHatBrick],
        ).register_hat(
            self.SalesOrder,
            main_brick_cls=bricks.SalesOrderBarHatBrick,
            secondary_brick_classes=[bricks.SalesOrderCardHatBrick],
        ).register_hat(
            self.TemplateBase,
            main_brick_cls=bricks.TemplateBaseBarHatBrick,
            # secondary_brick_classes=[bricks.TemplateBaseCardHatBrick],
        )

    def register_bulk_update(self, bulk_update_registry):
        from .forms.number_generation import NumberOverrider

        register = bulk_update_registry.register
        for model in (self.Invoice, self.Quote, self.SalesOrder, self.CreditNote):
            register(model).add_overriders(NumberOverrider)

        register(self.TemplateBase)  # TODO: what about number?
        register(self.ProductLine).exclude('on_the_fly_item')
        register(self.ServiceLine).exclude('on_the_fly_item')

    def register_buttons(self, button_registry):
        from . import buttons

        button_registry.register(
            buttons.GenerateNumberButton,
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
            bricks.NumberGeneratorItemsBrick,
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

    def register_cloners(self, entity_cloner_registry):
        from . import cloners

        entity_cloner_registry.register(
            model=self.Invoice, cloner_class=cloners.InvoiceCloner,
        ).register(
            model=self.Quote, cloner_class=cloners.QuoteCloner,
        ).register(
            model=self.SalesOrder, cloner_class=cloners.SalesOrderCloner,
        ).register(
            model=self.CreditNote, cloner_class=cloners.CreditNoteCloner,
        ).register(
            model=self.ProductLine,
        ).register(
            model=self.ServiceLine,
        )
        # NB: TemplateBase can not be cloned
        #     (because it is closely linked to its RecurrentGenerator)

    def register_deletors(self, entity_deletor_registry):
        entity_deletor_registry.register(
            model=self.Invoice,
        ).register(
            model=self.Quote,
        ).register(
            model=self.SalesOrder,
        ).register(
            model=self.CreditNote,
        ).register(
            model=self.ProductLine,
        ).register(
            model=self.ServiceLine,
        )
        # NB: TemplateBase can not be deleted directly
        #     (because it is closely linked to its RecurrentGenerator)

    def register_fields_config(self, fields_config_registry):
        fields_config_registry.register_models(
            self.Invoice,
            self.Quote,
            self.SalesOrder,
            self.CreditNote,
            # TODO ?
            # self.TemplateBase,
            # self.ServiceLine,
            # self.ProductLine,
            # models.AdditionalInformation,
            # models.PaymentTerms,
            # models.PaymentInformation,
        )

    def register_field_printers(self, field_printer_registry):
        from django.db.models import ForeignKey

        from creme.creme_core.gui.field_printers import FKPrinter

        from . import models, utils
        from .models.fields import BillingDiscountField

        field_printer_registry.register_model_field_type(
            type=BillingDiscountField, printer=utils.print_discount, tags='html*',
        )

        # TODO: models.OneToOneField? ManyToManyField?
        for printer in field_printer_registry.printers_for_field_type(
            type=ForeignKey, tags='html*',
        ):
            for model in (
                models.InvoiceStatus,
                models.QuoteStatus,
                models.CreditNoteStatus,
                models.SalesOrderStatus,
            ):
                printer.register(model=model, printer=FKPrinter.print_fk_colored_html)

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
            setting_keys.emitter_edition_key,
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

    def register_statistics(self, statistic_registry):
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

        statistic_registry.register(
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
