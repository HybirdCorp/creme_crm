# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from creme_core.gui.block import Block

from persons.models import Contact

from products.models import Product, Service

from billing.models import Quote, Invoice, SalesOrder, ProductLine, ServiceLine

from constants import (REL_OBJ_LINKED_CONTACT,
                       REL_OBJ_LINKED_PRODUCT, REL_OBJ_LINKED_SERVICE,
                       REL_OBJ_RESPONSIBLE,
                       REL_OBJ_LINKED_QUOTE, REL_OBJ_LINKED_INVOICE, REL_OBJ_LINKED_SALESORDER)

_contact_ct_id = None

class LinkedContactsBlock(Block):
    id_           = Block.generate_id('opportunities', 'linked_contacts')
    verbose_name  = _(u'Contact liés')
    template_name = 'opportunities/templatetags/block_contacts.html'

    def detailview_display(self, context):
        global _contact_ct_id

        opp = context['object']

        if not _contact_ct_id:
            _contact_ct_id = ContentType.objects.get_for_model(Contact).id

        return self._render(self.get_block_template_context(context, opp.get_contacts(),
                                                            update_url='/opportunities/opportunity/%s/linked/contacts/reload/' % opp.pk,
                                                            predicate_id=REL_OBJ_LINKED_CONTACT,
                                                            ct_id=_contact_ct_id))


class LinkedProductsBlock(Block):
    id_           = Block.generate_id('opportunities', 'linked_products')
    verbose_name  = _(u'Produits liés')
    template_name = 'opportunities/templatetags/block_products.html'

    def __init__(self, *args, **kwargs):
        super(LinkedProductsBlock, self).__init__(*args, **kwargs)

        self._product_ct_id = None

    def detailview_display(self, context):
        opp = context['object']

        if not self._product_ct_id:
            self._product_ct_id = ContentType.objects.get_for_model(Product).id

        return self._render(self.get_block_template_context(context, opp.get_products(),
                                                            update_url='/opportunities/opportunity/%s/linked/products/reload/' % opp.pk,
                                                            predicate_id=REL_OBJ_LINKED_PRODUCT,
                                                            ct_id=self._product_ct_id))


class LinkedServicesBlock(Block):
    id_           = Block.generate_id('opportunities', 'linked_services')
    verbose_name  = _(u'Services liés')
    template_name = 'opportunities/templatetags/block_services.html'

    def __init__(self, *args, **kwargs):
        super(LinkedServicesBlock, self).__init__(*args, **kwargs)

        self._service_ct_id = None

    def detailview_display(self, context):
        opp = context['object']

        if not self._service_ct_id:
            self._service_ct_id = ContentType.objects.get_for_model(Service).id

        return self._render(self.get_block_template_context(context, opp.get_services(),
                                                            update_url='/opportunities/opportunity/%s/linked/services/reload/' % opp.pk,
                                                            predicate_id=REL_OBJ_LINKED_SERVICE,
                                                            ct_id=self._service_ct_id))


class ResponsiblesBlock(Block):
    id_           = Block.generate_id('opportunities', 'responsibles')
    verbose_name  = _(u'Responsables')
    template_name = 'opportunities/templatetags/block_responsibles.html'

    def detailview_display(self, context):
        global _contact_ct_id

        opp = context['object']

        if not _contact_ct_id:
            _contact_ct_id = ContentType.objects.get_for_model(Contact).id

        return self._render(self.get_block_template_context(context,
                                                            opp.get_responsibles(),
                                                            update_url='/opportunities/opportunity/%s/responsibles/reload/' % opp.pk,
                                                            predicate_id=REL_OBJ_RESPONSIBLE,
                                                            ct_id=_contact_ct_id))


class QuotesBlock(Block):
    id_           = Block.generate_id('opportunities', 'quotes')
    verbose_name  = _(u'Devis')
    template_name = 'opportunities/templatetags/block_quotes.html'

    def __init__(self, *args, **kwargs):
        super(QuotesBlock, self).__init__(*args, **kwargs)

        self._quote_ct_id = None

    def detailview_display(self, context):
        opp = context['object']

        if not self._quote_ct_id:
            self._quote_ct_id = ContentType.objects.get_for_model(Quote).id

        return self._render(self.get_block_template_context(context,
                                                            opp.get_quotes(),
                                                            update_url='/opportunities/opportunity/%s/linked/quotes/reload/' % opp.pk,
                                                            predicate_id=REL_OBJ_LINKED_QUOTE,
                                                            ct_id=self._quote_ct_id,
                                                            current_quote_id=opp.get_current_quote_id()))


class SalesOrdersBlock(Block):
    id_           = Block.generate_id('opportunities', 'sales_orders')
    verbose_name  = _(u'Bons de commande')
    template_name = 'opportunities/templatetags/block_sales_orders.html'

    def __init__(self, *args, **kwargs):
        super(SalesOrdersBlock, self).__init__(*args, **kwargs)

        self._salesorder_ct_id = None

    def detailview_display(self, context):
        opp = context['object']

        if not self._salesorder_ct_id:
            self._salesorder_ct_id = ContentType.objects.get_for_model(SalesOrder).id

        block_context = self.get_block_template_context(context, opp.get_salesorder(),
                                                        update_url='/opportunities/opportunity/%s/linked/sales_orders/reload/' % opp.pk,
                                                        predicate_id=REL_OBJ_LINKED_SALESORDER,
                                                        ct_id=self._salesorder_ct_id)

        return self._render(block_context)


class InvoicesBlock(Block):
    id_           = Block.generate_id('opportunities', 'invoices')
    verbose_name  = _(u'Factures')
    template_name = 'opportunities/templatetags/block_invoices.html'

    def __init__(self, *args, **kwargs):
        super(InvoicesBlock, self).__init__(*args, **kwargs)

        self._invoice_ct_id = None

    def detailview_display(self, context):
        opp = context['object']

        if not self._invoice_ct_id:
            self._invoice_ct_id = ContentType.objects.get_for_model(Invoice).id

        return self._render(self.get_block_template_context(context,
                                                            opp.get_invoices(),
                                                            update_url='/opportunities/opportunity/%s/linked/invoices/reload/' % opp.pk,
                                                            predicate_id=REL_OBJ_LINKED_INVOICE,
                                                            ct_id=self._invoice_ct_id))


class LinkedProductLinesBlock(Block):
    id_           = Block.generate_id('opportunities', 'linked_line_product_lines')
    verbose_name  = _(u'Produits liés')
    template_name = 'billing/templatetags/block_product_line.html'

    #def __init__(self, *args, **kwargs):
        #super(LinkedProductLinesBlock, self).__init__(*args, **kwargs)

    def detailview_display(self, context):
        pk = context['object'].pk
        return self._render(self.get_block_template_context(context, ProductLine.objects.filter(document=pk),
                                                            update_url='/opportunities/%s/product_lines/reload/' % pk))


class LinkedServiceLinesBlock(Block):
    id_           = Block.generate_id('opportunities', 'linked_service_lines')
    verbose_name  = _(u'Services liés')
    template_name = 'billing/templatetags/block_service_line.html'

    #def __init__(self, *args, **kwargs):
        #super(LinkedServiceLinesBlock, self).__init__(*args, **kwargs)

    def detailview_display(self, context):
        pk = context['object'].pk
        return self._render(self.get_block_template_context(context, ServiceLine.objects.filter(document=pk),
                                                            update_url='/opportunities/%s/service_lines/reload/' % pk))


linked_contacts_block = LinkedContactsBlock()
linked_products_block = LinkedProductsBlock()
linked_services_block = LinkedServicesBlock()
responsibles_block    = ResponsiblesBlock()
quotes_block          = QuotesBlock()
sales_orders_block    = SalesOrdersBlock()
invoices_block        = InvoicesBlock()
linked_product_lines_block = LinkedProductLinesBlock()
linked_service_lines_block = LinkedServiceLinesBlock()