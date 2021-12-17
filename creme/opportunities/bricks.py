# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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
from typing import Tuple, Type

from django.apps import apps
from django.core.paginator import Paginator
from django.db.models.query_utils import FilteredRelation, Q
from django.utils.translation import gettext_lazy as _

from creme import persons, products
from creme.creme_core.gui.bricks import (
    Brick,
    BrickDependencies,
    EntityBrick,
    QuerysetBrick,
    SimpleBrick,
)
from creme.creme_core.models import Relation
from creme.persons.bricks import Activities4Card, CommercialActs4Card
from creme.persons.constants import REL_SUB_EMPLOYED_BY

from . import constants, get_opportunity_model

Contact = persons.get_contact_model()
Organisation = persons.get_organisation_model()
Product = products.get_product_model()
Service = products.get_service_model()
Opportunity = get_opportunity_model()


class _RelatedToOpportunity:
    def get_related_queryset(self, *, opportunity, model, rtype_id):
        return model.objects.annotate(
            relations_w_opp=FilteredRelation(
                'relations',
                condition=Q(relations__object_entity=opportunity.id),
            ),
        ).filter(
            is_deleted=False,
            relations_w_opp__type=rtype_id,
        )

    def get_related_contacts(self, *, opportunity, rtype_id):
        return self.get_related_queryset(
            opportunity=opportunity, model=Contact, rtype_id=rtype_id,
        ).select_related('civility')


class OpportunityCardHatBrick(_RelatedToOpportunity, Brick):
    id_ = Brick._generate_hat_id('opportunities', 'opportunity_card')
    verbose_name = _('Card header block')
    dependencies = [
        Opportunity,
        Organisation, Contact,
        Relation,
        *Activities4Card.dependencies,
        *CommercialActs4Card.dependencies,
    ]
    relation_type_deps = [
        REL_SUB_EMPLOYED_BY,
        constants.REL_OBJ_LINKED_CONTACT,
        *Activities4Card.relation_type_deps,
        *CommercialActs4Card.relation_type_deps
    ]
    template_name = 'opportunities/bricks/opportunity-hat-card.html'

    displayed_contacts_number = 5

    def detailview_display(self, context):
        opportunity = context['object']
        is_hidden = context['fields_configs'].get_for_model(Opportunity).is_fieldname_hidden

        if apps.is_installed('creme.activities'):
            from creme.activities import get_activity_model

            is_neglected = not get_activity_model().objects.future_linked(
                entity=opportunity,
                today=context['today'] - timedelta(days=30),
            ).exists()
        else:
            is_neglected = None

        target = opportunity.target

        return self._render(self.get_template_context(
            context,
            hidden_fields={
                fname
                for fname in ('estimated_sales', 'made_sales')
                if is_hidden(fname)
            },
            is_neglected=is_neglected,
            target=target,
            target_is_organisation=isinstance(target, Organisation),
            contacts=Paginator(
                self.get_related_contacts(
                    opportunity=opportunity,
                    rtype_id=constants.REL_SUB_LINKED_CONTACT,
                ),
                per_page=self.displayed_contacts_number,
            ).page(1),
            activities=Activities4Card.get(context, opportunity),
            acts=CommercialActs4Card.get(context, opportunity),
        ))


class OpportunityBrick(EntityBrick):
    verbose_name = _('Information on the opportunity')
    dependencies = (Opportunity, Relation)
    relation_type_deps = (constants.REL_OBJ_LINKED_QUOTE, )

    def _get_title(self, entity, context):
        return self.verbose_name


class _LinkedStuffBrick(QuerysetBrick):
    # id_ = SET ME
    # verbose_name = SET ME
    dependencies: BrickDependencies = (Relation,)
    # relation_type_deps = SET ME
    # template_name = SET ME
    target_ctypes = (Opportunity,)

    def _get_queryset(self, entity):  # Override
        pass

    def detailview_display(self, context):
        entity = context['object']

        return self._render(self.get_template_context(
            context,
            self._get_queryset(entity),
            predicate_id=self.relation_type_deps[0],
        ))


class LinkedContactsBrick(_RelatedToOpportunity, _LinkedStuffBrick):
    id_ = QuerysetBrick.generate_id('opportunities', 'linked_contacts')
    verbose_name = _('Linked Contacts')
    description = _(
        'Displays Contacts linked to the current Opportunity with a '
        'relationship «involves in the opportunity».\n'
        'App: Opportunities'
    )
    dependencies = (Relation, Contact)
    relation_type_deps = (constants.REL_OBJ_LINKED_CONTACT, )
    template_name = 'opportunities/bricks/contacts.html'

    def _get_queryset(self, entity):
        return self.get_related_contacts(
            opportunity=entity,
            rtype_id=constants.REL_SUB_LINKED_CONTACT,
        )


class LinkedProductsBrick(_RelatedToOpportunity, _LinkedStuffBrick):
    id_ = QuerysetBrick.generate_id('opportunities', 'linked_products')
    verbose_name = _('Related products')
    description = _(
        'Displays Products linked to the current Opportunity with a '
        'relationship (Product) «is linked to the opportunity».\n'
        'App: Opportunities'
    )
    dependencies = (Relation, Product)
    relation_type_deps = (constants.REL_OBJ_LINKED_PRODUCT, )
    template_name = 'opportunities/bricks/products.html'
    order_by = 'name'

    def _get_queryset(self, entity):
        return self.get_related_queryset(
            opportunity=entity,
            model=Product,
            rtype_id=constants.REL_SUB_LINKED_PRODUCT,
        )


class LinkedServicesBrick(_RelatedToOpportunity, _LinkedStuffBrick):
    id_ = QuerysetBrick.generate_id('opportunities', 'linked_services')
    verbose_name = _('Related services')
    description = _(
        'Displays Services linked to the current Opportunity with a '
        'relationship (Service) «is linked to the opportunity».\n'
        'App: Opportunities'
    )
    dependencies = (Relation, Service)
    relation_type_deps = (constants.REL_OBJ_LINKED_SERVICE, )
    template_name = 'opportunities/bricks/services.html'
    order_by = 'name'

    def _get_queryset(self, entity):
        return self.get_related_queryset(
            opportunity=entity,
            model=Service,
            rtype_id=constants.REL_SUB_LINKED_SERVICE,
        )


class BusinessManagersBrick(_RelatedToOpportunity, _LinkedStuffBrick):
    id_ = QuerysetBrick.generate_id('opportunities', 'responsibles')
    verbose_name = _('Business managers')
    description = _(
        'Displays Contacts linked to the current Opportunity with a '
        'relationship «is responsible for».\n'
        'App: Opportunities'
    )
    dependencies = (Relation, Contact)
    relation_type_deps = (constants.REL_OBJ_RESPONSIBLE, )
    template_name = 'opportunities/bricks/managers.html'

    def _get_queryset(self, entity):
        return self.get_related_contacts(
            opportunity=entity,
            rtype_id=constants.REL_SUB_RESPONSIBLE,
        )


class TargettingOpportunitiesBrick(QuerysetBrick):
    id_ = QuerysetBrick.generate_id('opportunities', 'target_organisations')
    verbose_name = _('Opportunities which target the Organisation / Contact')
    description = _(
        'Displays the Opportunities linked to the current Organisation / Contact '
        'with a relationship «targets the organisation/contact».\n'
        'App: Opportunities'
    )
    dependencies = (Relation, Opportunity)
    relation_type_deps = (constants.REL_OBJ_TARGETS, )
    template_name = 'opportunities/bricks/opportunities.html'
    target_ctypes = (Organisation, Contact)
    order_by = 'name'

    def detailview_display(self, context):
        entity = context['object']
        is_hidden = context['fields_configs'].get_for_model(Opportunity).is_fieldname_hidden

        return self._render(self.get_template_context(
            context,
            # TODO: filter deleted ??
            Opportunity.objects.filter(
                relations__object_entity=entity.id,
                relations__type=constants.REL_SUB_TARGETS,
            ),
            predicate_id=self.relation_type_deps[0],
            hidden_fields={
                fname
                for fname in ('estimated_sales', 'made_sales')
                if is_hidden(fname)
            },
            is_organisation=isinstance(object, Organisation),
            is_contact=isinstance(object, Contact),
        ))


class OppTotalBrick(SimpleBrick):
    id_ = SimpleBrick.generate_id('opportunities', 'total')
    verbose_name = _('Totals')
    description = _(
        'Displays the totals (exclusive of tax & inclusive of tax) of the '
        'current Opportunity.\n'
        'App: Opportunities'
    )
    dependencies = (Opportunity, Relation)
    relation_type_deps = (constants.REL_OBJ_LINKED_QUOTE,)
    template_name = 'opportunities/bricks/total.html'  # TODO: totals.html ?
    target_ctypes = (Opportunity,)


class OppTargetBrick(Brick):
    id_ = Brick.generate_id('opportunities', 'target')
    verbose_name = _('Target and source')
    description = _(
        'Displays the target & the source of the current Opportunity.\n'
        'They are Contacts or Organisations, linked with the relationships '
        '«targeted by the opportunity» & «has generated the opportunity».\n'
        'App: Opportunities'
    )
    dependencies = (Opportunity, Organisation, Relation)
    relation_type_deps = (constants.REL_SUB_TARGETS,)
    template_name = 'opportunities/bricks/target.html'
    target_ctypes = (Opportunity,)

    def __init__(self):
        super().__init__()
        self.display_source = display_source = (
            len(Organisation.objects.filter_managed_by_creme()) > 1
        )

        if display_source:
            self.relation_type_deps += (constants.REL_OBJ_EMIT_ORGA,)

    def detailview_display(self, context):
        return self._render(self.get_template_context(
            context,
            # NB: we do not use .count() in order to use/fill the QuerySet
            #     cache ; it will probably be used several times in the same
            #     page (and if not, this query should be small).
            display_source=self.display_source,
        ))


bricks_list: Tuple[Type[Brick], ...] = (
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
        id_ = QuerysetBrick.generate_id('opportunities', 'quotes')
        verbose_name = _('Quotes linked to the opportunity')
        description = _(
            'Displays Quotes linked to the current Opportunity with a '
            'relationship (Quote) «generated for the opportunity».\n'
            'App: Opportunities'
        )
        dependencies = (Relation, Quote)
        relation_type_deps = (constants.REL_OBJ_LINKED_QUOTE,)
        template_name = 'opportunities/bricks/quotes.html'
        order_by = 'name'

        def _get_queryset(self, entity):
            # TODO: test
            # TODO: filter deleted ?? what about current quote behaviour ??
            return Quote.objects.filter(
                relations__object_entity=entity.id,
                relations__type=constants.REL_SUB_LINKED_QUOTE,
            )

    class SalesOrdersBrick(_LinkedStuffBrick):
        id_ = QuerysetBrick.generate_id('opportunities', 'sales_orders')
        verbose_name = _('Salesorders linked to the opportunity')
        dependencies = (Relation, SalesOrder)
        description = _(
            'Displays Salesorders linked to the current Opportunity with a '
            'relationship (Salesorder) «generated for the opportunity».\n'
            'App: Opportunities'
        )
        relation_type_deps = (constants.REL_OBJ_LINKED_SALESORDER, )
        template_name = 'opportunities/bricks/sales-orders.html'
        order_by = 'name'

        def _get_queryset(self, entity):
            # TODO: test
            return SalesOrder.objects.filter(
                is_deleted=False,
                relations__object_entity=entity.id,
                relations__type=constants.REL_SUB_LINKED_SALESORDER,
            )

    class InvoicesBrick(_LinkedStuffBrick):
        id_ = QuerysetBrick.generate_id('opportunities', 'invoices')
        verbose_name = _('Invoices linked to the opportunity')
        dependencies = (Relation, Invoice)
        description = _(
            'Displays Invoices linked to the current Opportunity with a '
            'relationship (Invoice) «generated for the opportunity».\n'
            'App: Opportunities'
        )
        relation_type_deps = (constants.REL_OBJ_LINKED_INVOICE, )
        template_name = 'opportunities//bricks/invoices.html'
        order_by = 'name'

        def _get_queryset(self, entity):
            # TODO: test
            return Invoice.objects.filter(
                is_deleted=False,
                relations__object_entity=entity.id,
                relations__type=constants.REL_SUB_LINKED_INVOICE,
            )

    bricks_list += (
        QuotesBrick,
        SalesOrdersBrick,
        InvoicesBrick,
    )
