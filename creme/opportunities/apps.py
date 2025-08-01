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

import logging

from django.utils.translation import gettext_lazy as _

from creme.creme_core.apps import CremeAppConfig

logger = logging.getLogger(__name__)


class OpportunitiesConfig(CremeAppConfig):
    default = True
    name = 'creme.opportunities'
    verbose_name = _('Opportunities')
    dependencies = ['creme.persons', 'creme.products']

    def ready(self):
        super().ready()

        from django.apps import apps
        self.billing_installed = apps.is_installed('creme.billing')

    def all_apps_ready(self):
        from . import get_opportunity_model

        self.Opportunity = get_opportunity_model()
        super().all_apps_ready()

        if self.MIGRATION_MODE:
            return

        if self.billing_installed:
            self.register_billing()

        from . import signals  # NOQA

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.Opportunity)

    def register_bricks(self, brick_registry):
        from . import bricks

        Opportunity = self.Opportunity
        brick_registry.register(
            *bricks.brick_classes
        ).register_4_model(
            Opportunity, bricks.OpportunityBrick,
        ).register_hat(
            Opportunity,
            secondary_brick_classes=(bricks.OpportunityCardHatBrick,),
        )

    def register_bulk_update(self, bulk_update_registry):
        bulk_update_registry.register(self.Opportunity)

    def register_buttons(self, button_registry):
        from . import buttons

        button_registry.register(*buttons.button_classes)

    def register_creme_config(self, config_registry):
        from . import models

        register_model = config_registry.register_model
        register_model(models.Origin,     'origin')
        register_model(models.SalesPhase, 'sales_phase')

    def register_custom_forms(self, cform_registry):
        from . import custom_forms

        cform_registry.register(
            custom_forms.OPPORTUNITY_CREATION_CFORM,
            custom_forms.OPPORTUNITY_EDITION_CFORM,
        )

    def register_cloners(self, entity_cloner_registry):
        from . import cloners

        entity_cloner_registry.register(
            model=self.Opportunity, cloner_class=cloners.OpportunityCloner,
        )

    def register_deletors(self, entity_deletor_registry):
        entity_deletor_registry.register(model=self.Opportunity)

    def register_fields_config(self, fields_config_registry):
        fields_config_registry.register_models(self.Opportunity)

    def register_field_printers(self, field_printer_registry):
        from django.db.models import ForeignKey

        from creme.creme_core.gui.field_printers import FKPrinter

        from .models import SalesPhase

        # TODO: models.OneToOneField? ManyToManyField?
        for printer in field_printer_registry.printers_for_field_type(
            type=ForeignKey, tags='html*',
        ):
            printer.register(model=SalesPhase, printer=FKPrinter.print_fk_colored_html)

    def register_function_fields(self, function_field_registry):
        from .function_fields import TurnoverField

        function_field_registry.register(self.Opportunity, TurnoverField)

    def register_icons(self, icon_registry):
        icon_registry.register(self.Opportunity, 'images/opportunity_%(size)s.png')

    def register_mass_import(self, import_form_registry):
        from .forms import mass_import

        import_form_registry.register(self.Opportunity, mass_import.get_mass_form_builder)

    def register_menu_entries(self, menu_registry):
        from . import menu

        menu_registry.register(
            menu.OpportunitiesEntry,
            menu.OpportunityCreationEntry,
        )

    def register_creation_menu(self, creation_menu_registry):
        creation_menu_registry.get_or_create_group(
            'opportunities-commercial', _('Commercial'), priority=20,
        ).add_link(
            'opportunities-create_opportunity', self.Opportunity, priority=3,
        )

    def register_setting_keys(self, setting_key_registry):
        from . import setting_keys

        setting_key_registry.register(
            setting_keys.quote_key,
            setting_keys.target_constraint_key,
            setting_keys.emitter_constraint_key,
            setting_keys.unsuccessful_key,
        )

    def register_smart_columns(self, smart_columns_registry):
        from .constants import REL_SUB_TARGETS

        smart_columns_registry.register_model(self.Opportunity) \
                              .register_field('name') \
                              .register_field('sales_phase') \
                              .register_relationtype(REL_SUB_TARGETS)

    def register_statistics(self, statistic_registry):
        from creme.persons import get_organisation_model

        from .statistics import CurrentYearStatistics

        statistic_registry.register(
            id='opportunities',
            label=CurrentYearStatistics.label,
            func=CurrentYearStatistics(
                opp_model=self.Opportunity,
                orga_model=get_organisation_model()
            ),
            perm='opportunities', priority=15,
        )

    def register_billing(self):
        from creme import billing
        from creme.billing.core.conversion import converter_registry

        from . import billing_converters

        Invoice    = billing.get_invoice_model()
        Quote      = billing.get_quote_model()
        SalesOrder = billing.get_sales_order_model()

        def add_converter(source_model, target_model, converter_cls):
            cls = converter_registry.get_converter_class(
                source_model=source_model, target_model=target_model,
            )
            if cls is None:
                logger.info(
                    'It seems there is no converter %s => %s, '
                    'no extra behaviour for Opportunity is added.',
                    source_model, target_model,
                )
            else:
                cls.post_save_copiers.append(converter_cls)

        add_converter(
            source_model=Quote, target_model=SalesOrder,
            converter_cls=billing_converters.QuoteToSalesOrderRelationAdder,
        )
        add_converter(
            source_model=Quote, target_model=Invoice,
            converter_cls=billing_converters.QuoteToInvoiceRelationAdder,
        )
        add_converter(
            source_model=SalesOrder, target_model=Invoice,
            converter_cls=billing_converters.SalesOrderToInvoiceRelationAdder,
        )
