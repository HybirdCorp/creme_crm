# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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
from django.utils.timezone import now
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required, permission_required

from creme.creme_core.models import Relation, CremeEntity
from creme.creme_core.utils.queries import get_first_or_None
from creme.creme_core.views.decorators import POST_only
from creme.creme_core.views.generic import (add_entity, add_model_with_popup,
                                          edit_entity, view_entity, list_view)
from creme.creme_core.utils import get_ct_or_404

from creme.persons.workflow import transform_target_into_customer, transform_target_into_prospect

from creme.products.models import Product

from creme.billing.models import Quote, Invoice, SalesOrder, ProductLine, ServiceLine, Vat
from creme.billing.constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED

from creme.opportunities.models import Opportunity, SalesPhase
from creme.opportunities.forms.opportunity import OpportunityCreateForm, OpportunityEditForm
from creme.opportunities.constants import *


@login_required
@permission_required('opportunities')
@permission_required('opportunities.add_opportunity')
def add(request):
    return add_entity(request, OpportunityCreateForm,
                      extra_initial={'sales_phase':  get_first_or_None(SalesPhase)}
                     )

@login_required
@permission_required('opportunities')
@permission_required('opportunities.add_opportunity')
def add_to(request, ce_id, inner_popup=False):
    centity = get_object_or_404(CremeEntity, pk=ce_id).get_real_entity()
    user = request.user

    user.has_perm_to_link_or_die(centity)
    # We don't need the link credentials with future Opportunity because
    # Target/emitter relationships are internal (they are mandatory
    # and can be seen as ForeignKeys).

    initial = {'target': '{"ctype":"%s","entity":"%s"}' % (centity.entity_type_id, centity.id), #TODO: This is not an easy way to init the field...
               'sales_phase': get_first_or_None(SalesPhase),
              }

    if inner_popup:
        response = add_model_with_popup(request, OpportunityCreateForm,
                                        title=_(u'New opportunity related to <%s>') %
                                                    centity.allowed_unicode(user),
                                        initial=initial,
                                       )
    else:
        response = add_entity(request, OpportunityCreateForm, extra_initial=initial)

    return response

@login_required
@permission_required('opportunities')
def edit(request, opp_id):
    return edit_entity(request, opp_id, Opportunity, OpportunityEditForm)

@login_required
@permission_required('opportunities')
def detailview(request, opp_id):
    return view_entity(request, opp_id, Opportunity, '/opportunities/opportunity',
                       'opportunities/view_opportunity.html',
                      )

@login_required
@permission_required('opportunities')
def listview(request):
    return list_view(request, Opportunity, extra_dict={'add_url': '/opportunities/opportunity/add'})


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
    Relation.populate_real_object_entities(relations)

    #TODO: Missing test case
    for relation in relations:
        item = relation.object_entity.get_real_entity()
        line_klass = ProductLine if isinstance(item, Product) else ServiceLine
        line_klass.objects.create(related_item=item,
                                  related_document=document,
                                  unit_price=item.unit_price,
                                  unit=item.unit,
                                  vat_value=Vat.get_default_vat(), #TODO: cache ?
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
        return HttpResponse("", mimetype="text/javascript")

    return redirect(opp)
