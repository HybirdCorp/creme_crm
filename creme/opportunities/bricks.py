# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2017  Hybird
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

from datetime import timedelta

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.gui.bricks import Brick, SimpleBrick, QuerysetBrick, EntityBrick
from creme.creme_core.models import Relation

from creme import persons, products
from creme.persons.bricks import Activities4Card, CommercialActs4Card
from creme.persons.constants import REL_SUB_EMPLOYED_BY

from . import get_opportunity_model, constants


Contact = persons.get_contact_model()
Organisation = persons.get_organisation_model()
Product = products.get_product_model()
Service = products.get_service_model()
Opportunity = get_opportunity_model()
_get_ct = ContentType.objects.get_for_model


class OpportunityCardHatBrick(Brick):
    id_           = SimpleBrick._generate_hat_id('opportunities', 'opportunity_card')
    dependencies  = [Opportunity, Organisation, Contact, Relation] + Activities4Card.dependencies\
                                                                   + CommercialActs4Card.dependencies
    relation_type_deps = [REL_SUB_EMPLOYED_BY] + Activities4Card.relation_type_deps\
                                               + CommercialActs4Card.relation_type_deps
    verbose_name  = _(u'Card header block')
    template_name = 'opportunities/bricks/opportunity-hat-card.html'

    def detailview_display(self, context):
        opportunity = context['object']
        is_hidden = context['fields_configs'].get_4_model(Opportunity).is_fieldname_hidden

        if apps.is_installed('creme.activities'):
            from creme.activities import get_activity_model

            is_neglected = not get_activity_model().get_future_linked(opportunity,
                                                                      today=context['today'] - timedelta(days=30),
                                                                     ).exists()
        else:
            is_neglected = None

        target = opportunity.target

        return self._render(self.get_template_context(
                    context,
                    hidden_fields={fname
                                       for fname in ('estimated_sales', 'made_sales')
                                           if is_hidden(fname)
                                  },
                    is_neglected=is_neglected,
                    target=target,
                    target_is_organisation=isinstance(target, Organisation),
                    activities=Activities4Card.get(context, opportunity),
                    acts=CommercialActs4Card.get(context, opportunity),
        ))


class OpportunityBrick(EntityBrick):
    verbose_name = _(u'Information on the opportunity')
    dependencies  = (Opportunity, Relation)
    relation_type_deps = (constants.REL_OBJ_LINKED_QUOTE, )

    def _get_title(self, entity, context):
        return self.verbose_name


class _LinkedStuffBrick(QuerysetBrick):
    # id_           = SET ME
    dependencies  = (Relation,)
    # relation_type_deps = SET ME
    # verbose_name  = SET ME
    # template_name = SET ME
    target_ctypes = (Opportunity,)

    _model = Contact  # DEPRECATED

    def _get_queryset(self, entity):  # Overload
        pass

    def detailview_display(self, context):
        entity = context['object']

        return self._render(self.get_template_context(
                    context,
                    self._get_queryset(entity),
                    # update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, entity.pk),
                    update_url=reverse('creme_core__reload_detailview_blocks', args=(self.id_, entity.pk)),
                    predicate_id=self.relation_type_deps[0],
                    ct=_get_ct(self._model),  # DEPRECATED (use 'objects_ctype' instead)
        ))


class LinkedContactsBrick(_LinkedStuffBrick):
    id_           = QuerysetBrick.generate_id('opportunities', 'linked_contacts')
    dependencies  = (Relation, Contact)
    relation_type_deps = (constants.REL_OBJ_LINKED_CONTACT, )
    verbose_name  = _(u'Linked Contacts')
    # template_name = 'opportunities/templatetags/block_contacts.html'
    template_name = 'opportunities/bricks/contacts.html'

    def _get_queryset(self, entity):
        return entity.get_contacts().select_related('civility')


class LinkedProductsBrick(_LinkedStuffBrick):
    id_           = QuerysetBrick.generate_id('opportunities', 'linked_products')
    dependencies  = (Relation, Product)
    relation_type_deps = (constants.REL_OBJ_LINKED_PRODUCT, )
    verbose_name  = _(u'Linked Products')
    # template_name = 'opportunities/templatetags/block_products.html'
    template_name = 'opportunities/bricks/products.html'
    order_by      = 'name'

    _model = Product

    def _get_queryset(self, entity):
        return entity.get_products()


class LinkedServicesBrick(_LinkedStuffBrick):
    id_           = QuerysetBrick.generate_id('opportunities', 'linked_services')
    dependencies  = (Relation, Service)
    relation_type_deps = (constants.REL_OBJ_LINKED_SERVICE, )
    verbose_name  = _(u'Linked Services')
    # template_name = 'opportunities/templatetags/block_services.html'
    template_name = 'opportunities/bricks/services.html'
    order_by      = 'name'

    _model = Service

    def _get_queryset(self, entity):
        return entity.get_services()


class BusinessManagersBrick(_LinkedStuffBrick):
    id_           = QuerysetBrick.generate_id('opportunities', 'responsibles')
    dependencies  = (Relation, Contact)
    relation_type_deps = (constants.REL_OBJ_RESPONSIBLE, )
    verbose_name  = _(u'Business managers')
    # template_name = 'opportunities/templatetags/block_responsibles.html'
    template_name = 'opportunities/bricks/managers.html'

    def _get_queryset(self, entity):
        return entity.get_responsibles().select_related('civility')


class TargettingOpportunitiesBrick(QuerysetBrick):
    id_           = QuerysetBrick.generate_id('opportunities', 'target_organisations')
    dependencies  = (Relation, Opportunity)
    relation_type_deps = (constants.REL_OBJ_TARGETS, )
    verbose_name  = _(u'Opportunities which target the organisation / contact')
    # template_name = 'opportunities/templatetags/block_opportunities.html'
    template_name = 'opportunities/bricks/opportunities.html'
    target_ctypes = (Organisation, Contact)
    order_by      = 'name'

    def detailview_display(self, context):
        entity = context['object']
        is_hidden = context['fields_configs'].get_4_model(Opportunity).is_fieldname_hidden

        return self._render(self.get_template_context(
                    context,
                    # TODO: filter deleted ??
                    Opportunity.objects.filter(relations__object_entity=entity.id,
                                               relations__type=constants.REL_SUB_TARGETS,
                                              ),
                    # update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, entity.pk),
                    update_url=reverse('creme_core__reload_detailview_blocks', args=(self.id_, entity.pk)),
                    predicate_id=self.relation_type_deps[0],
                    ct=_get_ct(Opportunity),  # DEPRECATED (use 'objects_ctype' instead)
                    hidden_fields={fname
                                    for fname in ('estimated_sales', 'made_sales')
                                        if is_hidden(fname)
                                  },
                    is_organisation=isinstance(object, Organisation),
                    is_contact=isinstance(object, Contact),
        ))


class OppTotalBrick(SimpleBrick):
    id_                 = SimpleBrick.generate_id('opportunities', 'total')
    dependencies        = (Opportunity, Relation)
    relation_type_deps  = (constants.REL_OBJ_LINKED_QUOTE,)
    verbose_name        = _(u'Total')
    # template_name       = 'opportunities/templatetags/block_total.html'
    template_name       = 'opportunities/bricks/total.html'
    target_ctypes       = (Opportunity,)


class OppTargetBrick(Brick):
    id_           = Brick.generate_id('opportunities', 'target')
    dependencies  = (Opportunity, Organisation, Relation)
    relation_type_deps = (constants.REL_SUB_TARGETS,)
    verbose_name  = _(u'Target and source')
    template_name = 'opportunities/bricks/target.html'
    target_ctypes = (Opportunity,)

    def __init__(self):
        super(OppTargetBrick, self).__init__()
        self.display_source = display_source = len(Organisation.get_all_managed_by_creme()) > 1

        if display_source:
            self.relation_type_deps += (constants.REL_OBJ_EMIT_ORGA,)

    def detailview_display(self, context):
        return self._render(self.get_template_context(
                    context,
                    # NB: we do not use .count() in order to use/fill the QuerySet cache ; it will probably
                    #     be used several times in the same page (and if not, this query should be small).
                    display_source=self.display_source,
        ))



bricks_list = (
    LinkedContactsBrick,
    LinkedProductsBrick,
    LinkedServicesBrick,
    BusinessManagersBrick,
    OppTotalBrick,
    OppTargetBrick,
    TargettingOpportunitiesBrick,
)


if apps.is_installed('creme.billing'):
    from creme import billing

    Invoice    = billing.get_invoice_model()
    Quote      = billing.get_quote_model()
    SalesOrder = billing.get_sales_order_model()

    class QuotesBrick(_LinkedStuffBrick):
        id_                = QuerysetBrick.generate_id('opportunities', 'quotes')
        dependencies       = (Relation, Quote)
        relation_type_deps = (constants.REL_OBJ_LINKED_QUOTE,)
        verbose_name       = _(u'Quotes linked to the opportunity')
        # template_name      = 'opportunities/templatetags/block_quotes.html'
        template_name      = 'opportunities/bricks/quotes.html'
        order_by           = 'name'

        _model = Quote

        def _get_queryset(self, entity):
            # TODO: test
            # TODO: filter deleted ?? what about current quote behaviour ??
            return Quote.objects.filter(relations__object_entity=entity.id,
                                        relations__type=constants.REL_SUB_LINKED_QUOTE,
                                       )


    class SalesOrdersBrick(_LinkedStuffBrick):
        id_                = QuerysetBrick.generate_id('opportunities', 'sales_orders')
        dependencies       = (Relation, SalesOrder)
        relation_type_deps = (constants.REL_OBJ_LINKED_SALESORDER, )
        verbose_name       = _(u'Salesorders linked to the opportunity')
        # template_name      = 'opportunities/templatetags/block_sales_orders.html'
        template_name      = 'opportunities/bricks/sales-orders.html'
        order_by           = 'name'

        _model = SalesOrder

        def _get_queryset(self, entity):
            # TODO: test
            return SalesOrder.objects.filter(is_deleted=False,
                                             relations__object_entity=entity.id,
                                             relations__type=constants.REL_SUB_LINKED_SALESORDER,
                                            )


    class InvoicesBrick(_LinkedStuffBrick):
        id_                = QuerysetBrick.generate_id('opportunities', 'invoices')
        dependencies       = (Relation, Invoice)
        relation_type_deps = (constants.REL_OBJ_LINKED_INVOICE, )
        verbose_name       = _(u'Invoices linked to the opportunity')
        # template_name      = 'opportunities/templatetags/block_invoices.html'
        template_name      = 'opportunities//bricks/invoices.html'
        order_by           = 'name'

        _model = Invoice

        def _get_queryset(self, entity):
            # TODO: test
            return Invoice.objects.filter(is_deleted=False,
                                          relations__object_entity=entity.id,
                                          relations__type=constants.REL_SUB_LINKED_INVOICE,
                                         )


    bricks_list += (
        QuotesBrick,
        SalesOrdersBrick,
        InvoicesBrick,
    )
