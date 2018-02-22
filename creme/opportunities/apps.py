# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2018  Hybird
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

from django.utils.translation import ugettext_lazy as _, pgettext, npgettext

from creme.creme_core.apps import CremeAppConfig


logger = logging.getLogger(__name__)


class OpportunitiesConfig(CremeAppConfig):
    name = 'creme.opportunities'
    verbose_name = _(u'Opportunities')
    dependencies = ['creme.persons', 'creme.products']

    def ready(self):
        super(OpportunitiesConfig, self).ready()

        from django.apps import apps
        self.billing_installed = apps.is_installed('creme.billing')

    def all_apps_ready(self):
        from . import get_opportunity_model

        self.Opportunity = get_opportunity_model()
        super(OpportunitiesConfig, self).all_apps_ready()

        if self.MIGRATION_MODE:
            return

        if self.billing_installed:
            self.register_billing()

        from . import signals

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.Opportunity)

    def register_bricks(self, brick_registry):
        from . import bricks

        Opportunity = self.Opportunity
        brick_registry.register(*bricks.bricks_list)
        brick_registry.register_4_model(Opportunity, bricks.OpportunityBrick)
        brick_registry.register_hat(Opportunity, secondary_brick_classes=(bricks.OpportunityCardHatBrick,))

    def register_buttons(self, button_registry):
        # from . import buttons
        # button_registry.register(buttons.linked_opportunity_button)
        from . import buttons
        button_registry.register(buttons.LinkedOpportunityButton)

    def register_icons(self, icon_registry):
        icon_registry.register(self.Opportunity, 'images/opportunity_%(size)s.png')

    def register_mass_import(self, import_form_registry):
        from .forms.mass_import import get_mass_form_builder

        import_form_registry.register(self.Opportunity, get_mass_form_builder)

    def register_menu(self, creme_menu):
        from django.conf import settings

        Opportunity = self.Opportunity

        if settings.OLD_MENU:
            from django.core.urlresolvers import reverse_lazy as reverse
            from creme.creme_core.auth import build_creation_perm as cperm

            reg_item = creme_menu.register_app('opportunities', '/opportunities/').register_item
            reg_item(reverse('opportunities__portal'),             _(u'Portal of opportunities'), 'opportunities')
            reg_item(reverse('opportunities__list_opportunities'), _(u'All opportunities'),       'opportunities')
            reg_item(reverse('opportunities__create_opportunity'), Opportunity.creation_label,    cperm(Opportunity))
        else:
            URLItem = creme_menu.URLItem

            container = creme_menu.get('features') \
                                  .get_or_create(creme_menu.ContainerItem, 'opportunities-commercial', priority=30,
                                                 defaults={'label': _(u'Commercial')},
                                                ) \
                                  .add(URLItem.list_view('opportunities-opportunities', model=Opportunity), priority=10)
            creme_menu.get('creation', 'main_entities') \
                      .add(URLItem.creation_view('opportunities-create_opportunity', model=Opportunity), priority=50)

            create_any = creme_menu.get('creation', 'any_forms') \
                                   .get_or_create_group('opportunities-commercial', _(u'Commercial'), priority=20) \
                                   .add_link('opportunities-create_opportunity', Opportunity, priority=3)

            if self.billing_installed:
                from creme.billing import get_quote_model
                Quote = get_quote_model()

                container.add(URLItem.list_view('opportunities-quotes', model=Quote), priority=20)
                create_any.add_link('create_quote', Quote, priority=20)

    def register_setting_keys(self, setting_key_registry):
        from .setting_keys import quote_key

        setting_key_registry.register(quote_key)

    def register_smart_columns(self, smart_columns_registry):
        from .constants import REL_SUB_TARGETS

        smart_columns_registry.register_model(self.Opportunity) \
                              .register_field('name') \
                              .register_field('sales_phase') \
                              .register_relationtype(REL_SUB_TARGETS)

    def register_statistics(self, statistics_registry):
        Opportunity = self.Opportunity

        def won_opportunities():
            count = Opportunity.objects.filter(sales_phase__won=True).count()
            return npgettext('opportunities-stats', u'%s won', u'%s won', count) % count

        statistics_registry.register(
            id='opportunities', label=Opportunity._meta.verbose_name_plural,
            func=lambda: [won_opportunities(),
                          pgettext('opportunities-stats', u'%s in all') % Opportunity.objects.count(),
                         ],
            perm='opportunities', priority=10,
        )

    def register_billing(self):
        from creme.creme_core.models import RelationType

        from creme.billing import get_invoice_model, get_quote_model, get_sales_order_model
        from creme.billing.registry import relationtype_converter

        from .constants import REL_SUB_LINKED_SALESORDER, REL_SUB_LINKED_INVOICE, REL_SUB_LINKED_QUOTE

        get_rtype = RelationType.objects.get

        try:
            linked_salesorder = get_rtype(id=REL_SUB_LINKED_SALESORDER)
            linked_invoice    = get_rtype(id=REL_SUB_LINKED_INVOICE)
            linked_quote      = get_rtype(id=REL_SUB_LINKED_QUOTE)
        except Exception as e:
            logger.info("A problem occurred: %s\n"
                        "It can happen during unitests or during the 'populate' phase. "
                        "Otherwise, has the database correctly been populated?", e
                       )
        else:
            Invoice    = get_invoice_model()
            Quote      = get_quote_model()
            SalesOrder = get_sales_order_model()

            register_rtype = relationtype_converter.register
            register_rtype(Quote,      linked_quote,      SalesOrder, linked_salesorder)
            register_rtype(Quote,      linked_quote,      Invoice,    linked_invoice)
            register_rtype(SalesOrder, linked_salesorder, Invoice,    linked_invoice)
