# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeEntity, Relation
from creme_core.gui.block import Block, QuerysetBlock

from persons.models import Contact, Organisation

from products.models import Product, Service

from billing.models import Quote, Invoice, SalesOrder
from billing.blocks import ProductLinesBlock, ServiceLinesBlock, TotalBlock

from opportunities.constants import *
from opportunities.models import Opportunity


_get_ct = ContentType.objects.get_for_model


class OpportunityBlock(Block):
    id_           = Block.generate_id('opportunities', 'opportunity')
    dependencies  = (Opportunity,)
    verbose_name  = u'Info on an opportunity'
    template_name = 'opportunities/templatetags/block_opportunity.html'


class _LinkedStuffBlock(QuerysetBlock):
    #id_           = SET ME
    dependencies  = (Relation,) #Contact
    #relation_type_deps = SET ME
    #verbose_name  = SET ME
    #template_name = SET ME
    target_ctypes = (Opportunity,)

    _ct = _get_ct(Contact) #overload if needed

    def _get_queryset(self, entity): #overload
        pass

    def detailview_display(self, context):
        entity = context['object']
        btc = self.get_block_template_context(context,
                                              self._get_queryset(entity),
                                              update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, entity.pk),
                                              predicate_id=self.relation_type_deps[0],
                                              ct=self._ct,
                                             )

        CremeEntity.populate_credentials(btc['page'].object_list, context['user'])

        return self._render(btc)


class LinkedContactsBlock(_LinkedStuffBlock):
    id_           = QuerysetBlock.generate_id('opportunities', 'linked_contacts')
    relation_type_deps = (REL_OBJ_LINKED_CONTACT, )
    verbose_name  = _(u'Linked Contacts')
    template_name = 'opportunities/templatetags/block_contacts.html'

    def _get_queryset(self, entity):
        return entity.get_contacts().select_related('civility')


class LinkedProductsBlock(_LinkedStuffBlock):
    id_           = QuerysetBlock.generate_id('opportunities', 'linked_products')
    relation_type_deps = (REL_OBJ_LINKED_PRODUCT, )
    verbose_name  = _(u'Linked Products')
    template_name = 'opportunities/templatetags/block_products.html'

    _ct = _get_ct(Product)

    def _get_queryset(self, entity):
        return entity.get_products()


class LinkedServicesBlock(_LinkedStuffBlock):
    id_           = QuerysetBlock.generate_id('opportunities', 'linked_services')
    relation_type_deps = (REL_OBJ_LINKED_SERVICE, )
    verbose_name  = _(u'Linked Services')
    template_name = 'opportunities/templatetags/block_services.html'

    _ct = _get_ct(Service)

    def _get_queryset(self, entity):
        return entity.get_services()


class ResponsiblesBlock(_LinkedStuffBlock):
    id_           = QuerysetBlock.generate_id('opportunities', 'responsibles')
    relation_type_deps = (REL_OBJ_RESPONSIBLE, )
    verbose_name  = _(u'Responsibles')
    template_name = 'opportunities/templatetags/block_responsibles.html'

    def _get_queryset(self, entity):
        return entity.get_responsibles().select_related('civility')


class QuotesBlock(_LinkedStuffBlock):
    id_           = QuerysetBlock.generate_id('opportunities', 'quotes')
    relation_type_deps = (REL_OBJ_LINKED_QUOTE, )
    verbose_name  = _(u"Quotes linked to the opportunity")
    template_name = 'opportunities/templatetags/block_quotes.html'

    _ct = _get_ct(Quote)

    def _get_queryset(self, entity):
        return entity.get_quotes()


class SalesOrdersBlock(_LinkedStuffBlock):
    id_           = QuerysetBlock.generate_id('opportunities', 'sales_orders')
    relation_type_deps = (REL_OBJ_LINKED_SALESORDER, )
    verbose_name  = _(u"Salesorders linked to the opportunity")
    template_name = 'opportunities/templatetags/block_sales_orders.html'

    _ct = _get_ct(SalesOrder)

    def _get_queryset(self, entity):
        return entity.get_salesorder()


class InvoicesBlock(_LinkedStuffBlock):
    id_           = QuerysetBlock.generate_id('opportunities', 'invoices')
    relation_type_deps = (REL_OBJ_LINKED_INVOICE, )
    verbose_name  = _(u"Invoices linked to the opportunity")
    template_name = 'opportunities/templatetags/block_invoices.html'

    _ct = _get_ct(Invoice)

    def _get_queryset(self, entity):
        return entity.get_invoices()


class TargetOrganisationsBlock(_LinkedStuffBlock):
    id_           = QuerysetBlock.generate_id('opportunities', 'target_organisations')
    relation_type_deps = (REL_OBJ_TARGETS_ORGA, )
    verbose_name  = _(u"Opportunities which target the organisation")
    template_name = 'opportunities/templatetags/block_opportunities.html'
    #configurable  = True
    target_ctypes = (Organisation,)

    _ct = _get_ct(Opportunity)

    def _get_queryset(self, entity):
        return Opportunity.objects.filter(relations__object_entity=entity.id, relations__type=REL_SUB_TARGETS_ORGA)


class OppProductLinesBlock(ProductLinesBlock):
    id_           = Block.generate_id('opportunities', 'product_lines')
    target_ctypes = (Opportunity,)


class OppServiceLinesBlock(ServiceLinesBlock):
    id_           = Block.generate_id('opportunities', 'service_lines')
    target_ctypes = (Opportunity,)


class OppTotalBlock(TotalBlock):
    id_           = Block.generate_id('opportunities', 'total')
    target_ctypes = (Opportunity,)


linked_contacts_block = LinkedContactsBlock()
linked_products_block = LinkedProductsBlock()
linked_services_block = LinkedServicesBlock()
responsibles_block    = ResponsiblesBlock()
quotes_block          = QuotesBlock()
salesorders_block     = SalesOrdersBlock()
invoices_block        = InvoicesBlock()
total_block           = OppTotalBlock()

blocks_list = (
    linked_contacts_block,
    linked_products_block,
    linked_services_block,
    responsibles_block,
    quotes_block,
    salesorders_block,
    invoices_block,
    total_block,
    TargetOrganisationsBlock(),
    OppProductLinesBlock(),
    OppServiceLinesBlock(),
)
