# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2016  Hybird
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

    def all_apps_ready(self):
        from django.apps import apps

        from . import get_opportunity_model

        self.Opportunity = get_opportunity_model()
        super(OpportunitiesConfig, self).all_apps_ready()

        if self.MIGRATION_MODE:
            return

        if apps.is_installed('creme.billing'):
            self.register_billing()

        from . import signals

    # def register_creme_app(self, creme_registry):
    #     creme_registry.register_app('opportunities', _(u'Opportunities'), '/opportunities')

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.Opportunity)

    def register_blocks(self, block_registry):
        from .blocks import blocks_list, OpportunityBlock

        block_registry.register_4_model(self.Opportunity, OpportunityBlock())
        block_registry.register(*blocks_list)

    def register_buttons(self, button_registry):
        from .buttons import linked_opportunity_button

        button_registry.register(linked_opportunity_button)

    def register_icons(self, icon_registry):
        icon_registry.register(self.Opportunity, 'images/opportunity_%(size)s.png')

    def register_mass_import(self, import_form_registry):
        from .forms.mass_import import get_mass_form_builder

        import_form_registry.register(self.Opportunity, get_mass_form_builder)

    def register_menu(self, creme_menu):
        from django.core.urlresolvers import reverse_lazy as reverse

        from creme.creme_core.auth import build_creation_perm as cperm

        Opportunity = self.Opportunity
        reg_item = creme_menu.register_app('opportunities', '/opportunities/').register_item
        reg_item('/opportunities/',                            _(u'Portal of opportunities'), 'opportunities')
        reg_item(reverse('opportunities__list_opportunities'), _(u'All opportunities'),       'opportunities')
        reg_item(reverse('opportunities__create_opportunity'), Opportunity.creation_label,    cperm(Opportunity))

    def register_setting_key(self, setting_key_registry):
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
        # except RelationType.DoesNotExist as e:
        except Exception as e:
            logger.info("A problem occured: %s\n"
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
