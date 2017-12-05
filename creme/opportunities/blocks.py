# -*- coding: utf-8 -*-

import warnings

from django.apps import apps
from django.utils.translation import pgettext_lazy

from creme.creme_core.gui.block import SimpleBlock

from creme.persons import get_organisation_model

from .bricks import (
    Opportunity, Relation, constants,
    _LinkedStuffBrick as _LinkedStuffBlock,
    LinkedContactsBrick as LinkedContactsBlock,
    LinkedProductsBrick as LinkedProductsBlock,
    LinkedServicesBrick as LinkedServicesBlock,
    BusinessManagersBrick as ResponsiblesBlock,
    TargettingOpportunitiesBrick as TargettingOpportunitiesBlock,
    OppTotalBrick as OppTotalBlock,
)

warnings.warn('opportunities.blocks is deprecated ; use opportunities.bricks instead.', DeprecationWarning)


class OpportunityBlock(SimpleBlock):
    template_name = 'creme_core/templatetags/block_object.html'
    dependencies  = (Opportunity, Relation)
    relation_type_deps = (constants.REL_OBJ_LINKED_QUOTE, )


class OppTargetBlock(SimpleBlock):
    id_           = SimpleBlock.generate_id('opportunities', 'target')
    dependencies  = (Opportunity, get_organisation_model())
    verbose_name  = pgettext_lazy('opportunities', u'Target organisation')
    template_name = 'opportunities/templatetags/block_target.html'
    target_ctypes = (Opportunity,)


linked_contacts_block = LinkedContactsBlock()
linked_products_block = LinkedProductsBlock()
linked_services_block = LinkedServicesBlock()
responsibles_block    = ResponsiblesBlock()
total_block           = OppTotalBlock()
target_block          = OppTargetBlock()
targetting_opps_block = TargettingOpportunitiesBlock()

blocks_list = (
    linked_contacts_block,
    linked_products_block,
    linked_services_block,
    responsibles_block,
    total_block,
    target_block,
    targetting_opps_block,
)

if apps.is_installed('creme.billing'):
    from .bricks import (
        QuotesBrick as QuotesBlock,
        SalesOrdersBrick as SalesOrdersBlock,
        InvoicesBrick as InvoicesBlock,
    )

    quotes_block      = QuotesBlock()
    salesorders_block = SalesOrdersBlock()
    invoices_block    = InvoicesBlock()

    blocks_list += (
        quotes_block,
        salesorders_block,
        invoices_block,
    )
