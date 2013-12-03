# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013  Hybird
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

from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.timezone import now
#from django.utils.translation import ugettext as _

from creme.creme_core.views.decorators import POST_only
from creme.creme_core.models import Relation, Vat
from creme.creme_core.utils import get_ct_or_404

from creme.persons.workflow import transform_target_into_customer, transform_target_into_prospect

from creme.products.models import Product

from creme.billing.models import Quote, Invoice, SalesOrder, ProductLine, ServiceLine
from creme.billing.constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED

#from ..constants import REL_SUB_CURRENT_DOC
from ..constants import *
from ..models import Opportunity


@login_required
@permission_required('opportunities')
@POST_only
def current_quote(request, opp_id, quote_id, action):
    user = request.user
    has_perm_or_die = user.has_perm_to_link_or_die if action == 'set_current' else user.has_perm_to_unlink_or_die

    opp = get_object_or_404(Opportunity, pk=opp_id)
    has_perm_or_die(opp)

    quote = get_object_or_404(Quote, pk=quote_id)
    has_perm_or_die(quote)

    kwargs = {'subject_entity': quote,
              'type_id':        REL_SUB_CURRENT_DOC,
              'object_entity':  opp,
              'user':           user,
             }

    relations = Relation.objects.filter(**kwargs)

    if action == 'set_current':
        if not relations:
            Relation.objects.create(**kwargs)
    else:  # action == 'unset_current':
        relations.delete()

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")

    return redirect(opp)


_GEN_BEHAVIOURS = {
    #Value is (Relation type ID between the new doc & the opportunity,
    #          Set the Relationship 'Current doc' ?,
    #          Workflow function,
    #         )
    Quote:      (REL_SUB_LINKED_QUOTE,      True,  transform_target_into_prospect),
    Invoice:    (REL_SUB_LINKED_INVOICE,    False, transform_target_into_customer),
    SalesOrder: (REL_SUB_LINKED_SALESORDER, False, None),
}

@login_required
@permission_required('opportunities')
@POST_only
def generate_new_doc(request, opp_id, ct_id):
    ct_doc = get_ct_or_404(ct_id)
    klass = ct_doc.model_class()

    try:
        rtype_id, set_as_current, workflow_action = _GEN_BEHAVIOURS[klass]
    except KeyError:
        raise Http404('Bad billing document type')

    user = request.user
    user.has_perm_to_create_or_die(klass)
    user.has_perm_to_link_or_die(klass, owner=user) #TODO: check in template too (must upgrade 'has_perm' to use owner!=None)

    opp = get_object_or_404(Opportunity, id=opp_id)
    user.has_perm_to_link_or_die(opp)

    document = klass.objects.create(user=user, issuing_date=now(),
                                    status_id=1, currency=opp.currency,
                                   )

    create_relation = partial(Relation.objects.create, subject_entity=document, user=user)
    create_relation(type_id=REL_SUB_BILL_ISSUED,   object_entity=opp.emitter)
    create_relation(type_id=REL_SUB_BILL_RECEIVED, object_entity=opp.target)
    create_relation(type_id=rtype_id,              object_entity=opp)

    document.generate_number() #Need the relation with emitter orga
    document.name = u'%s(%s)' % (document.number, opp.name)
    document.save()

    relations = Relation.objects.filter(subject_entity=opp.id,
                                        type__in=[REL_OBJ_LINKED_PRODUCT, REL_OBJ_LINKED_SERVICE],
                                       ).select_related('object_entity')

    #TODO: Missing test case
    if relations:
        Relation.populate_real_object_entities(relations)
        vat_value = Vat.get_default_vat()

        for relation in relations:
            item = relation.object_entity.get_real_entity()
            line_klass = ProductLine if isinstance(item, Product) else ServiceLine
            line_klass.objects.create(related_item=item,
                                      related_document=document,
                                      unit_price=item.unit_price,
                                      unit=item.unit,
                                      vat_value=vat_value,
                                     )

    # Now, there can be several current docs
    # for relation in Relation.objects.filter(object_entity=opp.id,
    #                                         type=REL_SUB_CURRENT_DOC,
    #                                         subject_entity__entity_type=ct_doc,
    #                                        ):
    #     relation.delete()

    if set_as_current:
        create_relation(type_id=REL_SUB_CURRENT_DOC, object_entity=opp)

    if workflow_action:
        workflow_action(opp.emitter, opp.target, user)

    if request.is_ajax():
        return HttpResponse('', mimetype="text/javascript")

    return redirect(opp)
