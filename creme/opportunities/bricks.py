################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from __future__ import annotations

from datetime import timedelta

from django.apps import apps
from django.core.paginator import Paginator
from django.db.models.query_utils import FilteredRelation, Q
from django.utils.translation import gettext_lazy as _

from creme import persons, products
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.gui.bricks import (
    Brick,
    BrickDependencies,
    EntityBrick,
    QuerysetBrick,
    SimpleBrick,
)
from creme.creme_core.models import Relation, RelationType
from creme.persons.bricks import Activities4Card, CommercialActs4Card
from creme.persons.constants import REL_SUB_EMPLOYED_BY

from . import constants, get_opportunity_model

Contact = persons.get_contact_model()
Organisation = persons.get_organisation_model()
Product = products.get_product_model()
Service = products.get_service_model()
Opportunity = get_opportunity_model()


class _RelatedToOpportunity:
    def get_related_queryset(self, *, opportunity, model, rtype_id, exclude_deleted=True):
        qs = model.objects.annotate(
            relations_w_opp=FilteredRelation(
                'relations',
                condition=Q(relations__object_entity=opportunity.id),
            ),
        ).filter(relations_w_opp__type=rtype_id)

        if exclude_deleted:
            qs = qs.exclude(is_deleted=True)

        # TODO: system that select_related() fields used by __str__()
        if model is Contact:
            qs = qs.select_related('civility')

        return qs


class OpportunityCardHatBrick(_RelatedToOpportunity, Brick):
    # id_ = Brick._generate_hat_id('opportunities', 'opportunity_card')
    id = Brick._generate_hat_id('opportunities', 'opportunity_card')
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
                self.get_related_queryset(
                    opportunity=opportunity,
                    model=Contact,
                    # TODO: get the relation type id from the dependencies
                    #       (wait for RelationTypes cache)
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


class _LinkedStuffBrick(_RelatedToOpportunity, QuerysetBrick):
    # id = SET ME
    # verbose_name = SET ME
    dependencies: BrickDependencies = (Relation,)  # NB: needs a second model
    # relation_type_deps = SET ME
    # template_name = SET ME
    target_ctypes = (Opportunity,)

    # If True, entity marked as deleted are excluded from the query.
    exclude_deleted = True
    cells_desc = []

    def _get_queryset(self, opportunity, rtype):
        return self.get_related_queryset(
            opportunity=opportunity,
            model=self.dependencies[1],
            rtype_id=rtype.symmetric_type_id,
            exclude_deleted=self.exclude_deleted,
        )

    def detailview_display(self, context):
        entity = context['object']
        relation_type = RelationType.objects.get(id=self.relation_type_deps[0])

        cells = []
        for cell_class, cell_name in self.cells_desc:
            # cell = cell_class.build(Contact, cell_name)
            cell = cell_class.build(self.dependencies[1], cell_name)
            if cell is not None and not cell.is_excluded:
                cells.append(cell)

        return self._render(self.get_template_context(
            context,
            self._get_queryset(opportunity=entity, rtype=relation_type),
            relation_type=relation_type,
            cells=cells,
        ))


class LinkedContactsBrick(_LinkedStuffBrick):
    # id_ = QuerysetBrick.generate_id('opportunities', 'linked_contacts')
    id = _LinkedStuffBrick.generate_id('opportunities', 'linked_contacts')
    verbose_name = _('Linked Contacts')
    description = _(
        'Displays Contacts linked to the current Opportunity with a '
        'relationship «involves in the opportunity».\n'
        'App: Opportunities'
    )
    dependencies = (Relation, Contact)
    relation_type_deps = (constants.REL_OBJ_LINKED_CONTACT, )
    template_name = 'opportunities/bricks/contacts.html'

    cells_desc = [
        (EntityCellRegularField, 'position'),
        (EntityCellRegularField, 'email'),
        (EntityCellRegularField, 'phone'),
        (EntityCellRegularField, 'mobile'),
    ]


class LinkedProductsBrick(_LinkedStuffBrick):
    # id_ = QuerysetBrick.generate_id('opportunities', 'linked_products')
    id = _LinkedStuffBrick.generate_id('opportunities', 'linked_products')
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


class LinkedServicesBrick(_LinkedStuffBrick):
    # id_ = QuerysetBrick.generate_id('opportunities', 'linked_services')
    id = _LinkedStuffBrick.generate_id('opportunities', 'linked_services')
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


class BusinessManagersBrick(_LinkedStuffBrick):
    # id_ = QuerysetBrick.generate_id('opportunities', 'responsibles')
    id = _LinkedStuffBrick.generate_id('opportunities', 'responsibles')
    verbose_name = _('Business managers')
    description = _(
        'Displays Contacts linked to the current Opportunity with a '
        'relationship «is responsible for».\n'
        'App: Opportunities'
    )
    dependencies = (Relation, Contact)
    relation_type_deps = (constants.REL_OBJ_RESPONSIBLE, )
    template_name = 'opportunities/bricks/managers.html'

    # TODO: factorise ?
    cells_desc = [
        (EntityCellRegularField, 'position'),
        (EntityCellRegularField, 'email'),
        (EntityCellRegularField, 'phone'),
        (EntityCellRegularField, 'mobile'),
    ]


# class TargettingOpportunitiesBrick(QuerysetBrick):
class TargetingOpportunitiesBrick(QuerysetBrick):
    # id_ = QuerysetBrick.generate_id('opportunities', 'target_organisations')
    id = QuerysetBrick.generate_id('opportunities', 'target_organisations')
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
                # TODO: get the relation type id from the dependencies
                #       (wait for RelationTypes cache)
                relations__type=constants.REL_SUB_TARGETS,
            ),
            predicate_id=self.relation_type_deps[0],
            hidden_fields={
                fname
                for fname in ('estimated_sales', 'made_sales')
                if is_hidden(fname)
            },
            is_organisation=isinstance(entity, Organisation),
            is_contact=isinstance(entity, Contact),
        ))


class OppTotalBrick(SimpleBrick):
    # id_ = SimpleBrick.generate_id('opportunities', 'total')
    id = SimpleBrick.generate_id('opportunities', 'total')
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
    # id_ = Brick.generate_id('opportunities', 'target')
    id = Brick.generate_id('opportunities', 'target')
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


brick_classes: list[type[Brick]] = [
    LinkedContactsBrick,
    LinkedProductsBrick,
    LinkedServicesBrick,
    BusinessManagersBrick,
    OppTotalBrick,
    OppTargetBrick,
    TargetingOpportunitiesBrick,
]

if apps.is_installed('creme.billing'):
    from creme import billing

    Invoice    = billing.get_invoice_model()
    Quote      = billing.get_quote_model()
    SalesOrder = billing.get_sales_order_model()

    class QuotesBrick(_LinkedStuffBrick):
        # id_ = QuerysetBrick.generate_id('opportunities', 'quotes')
        id = _LinkedStuffBrick.generate_id('opportunities', 'quotes')
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

        # TODO: filter deleted ?? what about current quote behaviour ??
        exclude_deleted = False

    class SalesOrdersBrick(_LinkedStuffBrick):
        # id_ = QuerysetBrick.generate_id('opportunities', 'sales_orders')
        id = _LinkedStuffBrick.generate_id('opportunities', 'sales_orders')
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

    class InvoicesBrick(_LinkedStuffBrick):
        # id_ = QuerysetBrick.generate_id('opportunities', 'invoices')
        id = _LinkedStuffBrick.generate_id('opportunities', 'invoices')
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

    brick_classes += [
        QuotesBrick,
        SalesOrdersBrick,
        InvoicesBrick,
    ]
