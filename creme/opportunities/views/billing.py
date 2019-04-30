# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2019  Hybird
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

from django.db.transaction import atomic
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.models import Relation, Vat
from creme.creme_core.utils import get_ct_or_404
from creme.creme_core.views.decorators import POST_only

from creme.persons import workflow

from creme.products import get_product_model

from creme import billing
from creme.billing.constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED

from .. import constants
from .. import get_opportunity_model


Invoice     = billing.get_invoice_model()
Quote       = billing.get_quote_model()
SalesOrder  = billing.get_sales_order_model()
ProductLine = billing.get_product_line_model()
ServiceLine = billing.get_service_line_model()
Opportunity = get_opportunity_model()


@login_required
@permission_required('opportunities')
@POST_only
def current_quote(request, opp_id, quote_id, action):
    user = request.user
    has_perm_or_die = user.has_perm_to_link_or_die if action == 'set_current' else \
                      user.has_perm_to_unlink_or_die

    opp = get_object_or_404(Opportunity, pk=opp_id)
    has_perm_or_die(opp)

    quote = get_object_or_404(Quote, pk=quote_id)
    has_perm_or_die(quote)

    kwargs = {'subject_entity': quote,
              'type_id':        constants.REL_SUB_CURRENT_DOC,
              'object_entity':  opp,
              'user':           user,
             }

    relations = Relation.objects.filter(**kwargs)

    if action == 'set_current':
        if not relations:
            Relation.objects.safe_create(**kwargs)
    else:  # action == 'unset_current':
        relations.delete()

    if request.is_ajax():
        return HttpResponse()

    return redirect(opp)


_GEN_BEHAVIOURS = {
    # Value is (Relation type ID between the new doc & the opportunity,
    #           Set the Relationship 'Current doc' ?,
    #           Workflow function,
    #         )
    Quote:      (constants.REL_SUB_LINKED_QUOTE,      True,  workflow.transform_target_into_prospect),
    Invoice:    (constants.REL_SUB_LINKED_INVOICE,    False, workflow.transform_target_into_customer),
    SalesOrder: (constants.REL_SUB_LINKED_SALESORDER, False, None),
}


@login_required
@permission_required('opportunities')
@POST_only
@atomic
def generate_new_doc(request, opp_id, ct_id):
    ct_doc = get_ct_or_404(ct_id)
    klass = ct_doc.model_class()

    try:
        rtype_id, set_as_current, workflow_action = _GEN_BEHAVIOURS[klass]
    except KeyError as e:
        raise Http404('Bad billing document type') from e

    user = request.user
    user.has_perm_to_create_or_die(klass)
    user.has_perm_to_link_or_die(klass, owner=user)  # TODO: check in template too (must upgrade 'has_perm' to use owner!=None)

    opp = get_object_or_404(Opportunity, id=opp_id)
    user.has_perm_to_link_or_die(opp)

    document = klass.objects.create(user=user, issuing_date=now(),
                                    status_id=1, currency=opp.currency,
                                   )

    create_relation = partial(Relation.objects.create, subject_entity=document, user=user)
    create_relation(type_id=REL_SUB_BILL_ISSUED,   object_entity=opp.emitter)
    create_relation(type_id=REL_SUB_BILL_RECEIVED, object_entity=opp.target)
    create_relation(type_id=rtype_id,              object_entity=opp)

    document.generate_number()  # Need the relationship with emitter organisation
    document.name = _('{number} ({opportunity})').format(number=document.number, opportunity=opp.name)
    document.save()

    relations = Relation.objects.filter(subject_entity=opp.id,
                                        type__in=[constants.REL_OBJ_LINKED_PRODUCT,
                                                  constants.REL_OBJ_LINKED_SERVICE,
                                                 ],
                                       ).select_related('object_entity')

    # TODO: Missing test case
    if relations:
        Relation.populate_real_object_entities(relations)
        vat_value = Vat.get_default_vat()
        Product = get_product_model()

        for relation in relations:
            item = relation.object_entity.get_real_entity()
            line_klass = ProductLine if isinstance(item, Product) else ServiceLine
            line_klass.objects.create(related_item=item,
                                      related_document=document,
                                      unit_price=item.unit_price,
                                      unit=item.unit,
                                      vat_value=vat_value,
                                     )

    if set_as_current:
        create_relation(type_id=constants.REL_SUB_CURRENT_DOC, object_entity=opp)

    if workflow_action:
        workflow_action(opp.emitter, opp.target, user)

    if request.is_ajax():
        return HttpResponse()

    return redirect(opp)
