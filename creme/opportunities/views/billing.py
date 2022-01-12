# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2022  Hybird
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

from functools import partial

from django.db.models.query_utils import Q
from django.db.transaction import atomic
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme import billing
from creme.billing.constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED
from creme.creme_core.http import is_ajax
from creme.creme_core.models import Relation, SettingValue, Vat
from creme.creme_core.views.generic import base
from creme.creme_core.views.relation import RelationsObjectsSelectionPopup
from creme.persons import workflow
from creme.products import get_product_model

from .. import constants, get_opportunity_model
from ..setting_keys import emitter_constraint_key, target_constraint_key

Invoice     = billing.get_invoice_model()
Quote       = billing.get_quote_model()
SalesOrder  = billing.get_sales_order_model()
ProductLine = billing.get_product_line_model()
ServiceLine = billing.get_service_line_model()
Opportunity = get_opportunity_model()


class CurrentQuoteSetting(base.CheckedView):
    permissions = 'opportunities'

    action_url_kwarg = 'action'
    opp_id_url_kwarg = 'opp_id'
    quote_id_url_kwarg = 'quote_id'

    rtype_id = constants.REL_SUB_CURRENT_DOC

    def post(self, request, *args, **kwargs):
        user = request.user
        action = self.kwargs[self.action_url_kwarg]
        opp_id = self.kwargs[self.opp_id_url_kwarg]
        quote_id = self.kwargs[self.quote_id_url_kwarg]

        has_perm_or_die = (
            user.has_perm_to_link_or_die
            if action == 'set_current' else
            user.has_perm_to_unlink_or_die
        )

        opp = get_object_or_404(Opportunity, pk=opp_id)
        has_perm_or_die(opp)

        quote = get_object_or_404(Quote, pk=quote_id)
        has_perm_or_die(quote)

        kwargs = {
            'subject_entity': quote,
            'type_id': self.rtype_id,
            'object_entity': opp,
            'user': user,
        }

        relations = Relation.objects.filter(**kwargs)

        if action == 'set_current':
            if not relations:
                Relation.objects.safe_create(**kwargs)
        else:  # action == 'unset_current':
            relations.delete()

        # if request.is_ajax():
        if is_ajax(request):
            return HttpResponse()

        return redirect(opp)


class BillingDocGeneration(base.EntityCTypeRelatedMixin,
                           base.EntityRelatedMixin,
                           base.CheckedView):
    permissions = 'opportunities'
    entity_id_url_kwarg = 'opp_id'

    behaviours = {
        # Value is (Relation type ID between the new doc & the opportunity,
        #           Set the Relationship 'Current doc' ?,
        #           Workflow function,
        #         )
        Quote: (
            constants.REL_SUB_LINKED_QUOTE,
            True,
            workflow.transform_target_into_prospect,
        ),
        Invoice: (
            constants.REL_SUB_LINKED_INVOICE,
            False,
            workflow.transform_target_into_customer,
        ),
        SalesOrder: (constants.REL_SUB_LINKED_SALESORDER, False, None),
    }
    generated_name = '{document.number} — {opportunity}'

    def check_related_entity_permissions(self, entity, user):
        user.has_perm_to_link_or_die(entity)

    @atomic
    def post(self, request, *args, **kwargs):
        klass = self.get_ctype().model_class()

        try:
            rtype_id, set_as_current, workflow_action = self.behaviours[klass]
        except KeyError as e:
            raise Http404('Bad billing document type') from e

        user = request.user
        user.has_perm_to_create_or_die(klass)
        # TODO: check in template too (must upgrade 'has_perm' to use owner!=None)
        user.has_perm_to_link_or_die(klass, owner=user)

        opp = self.get_related_entity()

        b_document = klass.objects.create(
            user=user,
            issuing_date=now(),
            status_id=1,
            currency=opp.currency,
            source=opp.emitter,
            target=opp.target,
        )

        create_relation = partial(
            Relation.objects.create, subject_entity=b_document, user=user,
        )
        create_relation(type_id=rtype_id, object_entity=opp)

        b_document.generate_number()  # Need the relationship with emitter organisation
        b_document.name = self.generated_name.format(document=b_document, opportunity=opp)
        b_document.save()

        relations = Relation.objects.filter(
            subject_entity=opp.id,
            type__in=[
                constants.REL_OBJ_LINKED_PRODUCT,
                constants.REL_OBJ_LINKED_SERVICE,
            ],
        ).select_related('object_entity')

        # TODO: Missing test case
        if relations:
            Relation.populate_real_object_entities(relations)
            # vat_value = Vat.get_default_vat()
            vat_value = Vat.objects.default()
            Product = get_product_model()

            for relation in relations:
                item = relation.object_entity.get_real_entity()
                line_klass = ProductLine if isinstance(item, Product) else ServiceLine
                line_klass.objects.create(
                    related_item=item,
                    related_document=b_document,
                    unit_price=item.unit_price,
                    unit=item.unit,
                    vat_value=vat_value,
                )

        if set_as_current:
            create_relation(type_id=constants.REL_SUB_CURRENT_DOC, object_entity=opp)

        if workflow_action:
            workflow_action(opp.emitter, opp.target, user)

        # if request.is_ajax():
        if is_ajax(request):
            return HttpResponse()

        return redirect(opp)


# NB: we create a customised view for selection instead of using RelationsObjectsSelectionPopup
#     & the possibility to pass a q_filter (& change the title of client side) because
#     q_filter is not great for a double relationships filter (we cannot pass a sub-queryset
#     & pass a list of IDs in GET parameter is not scalable/straightforward)
class RelatedObjectsSelectionPopup(RelationsObjectsSelectionPopup):
    def __init__(self):
        super().__init__()
        self.constraints = None

    def get_constraints(self):
        constraints = self.constraints

        if constraints is None:
            svalues = SettingValue.objects.get_4_keys(
                {'key': target_constraint_key,  'default': True},
                {'key': emitter_constraint_key, 'default': True},
            )
            self.constraints = constraints = {
                'target':  svalues[target_constraint_key.id].value,
                'emitter': svalues[emitter_constraint_key.id].value,
            }

        return constraints

    def get_internal_q(self):
        extra_q = super().get_internal_q()
        constraints = self.get_constraints()

        if constraints['target']:
            extra_q &= Q(
                pk__in=Relation.objects.filter(
                    object_entity=self.get_related_entity().target.id,
                    type=REL_SUB_BILL_RECEIVED,
                ).values_list('subject_entity_id', flat=True),
            )

        if constraints['emitter']:
            extra_q &= Q(
                pk__in=Relation.objects.filter(
                    object_entity=self.get_related_entity().emitter.id,
                    type=REL_SUB_BILL_ISSUED,
                ).values_list('subject_entity_id', flat=True),
            )

        return extra_q

    def get_title(self):
        constraints = self.get_constraints()
        same_target = constraints['target']
        same_emitter = constraints['emitter']

        if same_target:
            models = self.model._meta.verbose_name_plural
            opp = self.get_related_entity()

            return (
                _('List of {models} issued by {emitter} and received by {target}').format(
                    models=models,
                    target=opp.target,
                    emitter=opp.emitter,
                )
                if same_emitter else
                _('List of {models} received by {target}').format(
                    models=models,
                    target=opp.target,
                )
            )
        elif same_emitter:
            return _('List of {models} issued by {emitter}').format(
                models=self.model._meta.verbose_name_plural,
                emitter=self.get_related_entity().emitter,
            )

        return super().get_title()
