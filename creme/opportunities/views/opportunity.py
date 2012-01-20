# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from datetime import datetime

from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required, permission_required
from billing.models.other_models import Vat

from creme_core.models import Relation, CremeEntity
from creme_core.views.generic import add_entity, add_model_with_popup, edit_entity, view_entity, list_view
from creme_core.utils import get_ct_or_404

from persons.workflow import transform_target_into_customer, transform_target_into_prospect

from products.models import Product, Service

from billing.models import Quote, Invoice, SalesOrder, Line, ProductLine, ServiceLine
from billing.constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED

from opportunities.models import Opportunity
from opportunities.forms.opportunity import OpportunityCreateForm, OpportunityEditForm
from opportunities.constants import REL_OBJ_LINKED_QUOTE, REL_OBJ_LINKED_INVOICE, REL_OBJ_LINKED_SALESORDER, REL_SUB_CURRENT_DOC, REL_OBJ_LINKED_SERVICE, REL_OBJ_LINKED_PRODUCT


@login_required
@permission_required('opportunities')
@permission_required('opportunities.add_opportunity')
def add(request):
    return add_entity(request, OpportunityCreateForm)

@login_required
@permission_required('opportunities')
@permission_required('opportunities.add_opportunity')
def add_to(request, ce_id, inner_popup=False):
    centity = get_object_or_404(CremeEntity, pk=ce_id).get_real_entity()
    user = request.user

    centity.can_link_or_die(user) #TODO: test the link creds with the future opp in the form.clean()

    initial = {"target": '{"ctype":"%s","entity":"%s"}' % (centity.entity_type_id, centity.id)}#TODO: This is not an easy way to init the field...

    if inner_popup:
        response = add_model_with_popup(request, OpportunityCreateForm,
                                    title=_(u'New opportunity related to <%s>') % centity.allowed_unicode(user),
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

_RELATIONS_DICT = {
            Quote:      REL_OBJ_LINKED_QUOTE,
            Invoice:    REL_OBJ_LINKED_INVOICE,
            SalesOrder: REL_OBJ_LINKED_SALESORDER,
        }

_CURRENT_DOC_DICT = {
            Quote:      True,
            Invoice:    False,
            SalesOrder: False
        }

_WORKFLOW_DICT = {
            Quote:      transform_target_into_prospect,
            Invoice:    transform_target_into_customer,
            SalesOrder: None
        }

@login_required
@permission_required('opportunities')
def generate_new_doc(request, opp_id, ct_id):
    if request.method != 'POST':
        raise Http404('This view accepts only POST method')

    ct_doc = get_ct_or_404(ct_id)
    opp    = get_object_or_404(Opportunity, id=opp_id)
    user   = request.user

    opp.can_link_or_die(user)

    #TODO: link credentials on the future doc too....

    klass = ct_doc.model_class()

    user.has_perm_to_create_or_die(klass)

    document = klass.objects.create(user=user, issuing_date=datetime.now(), status_id=1, currency=opp.currency,
                                    comment=_(u"Generated from the opportunity «%s»") % opp
                                   )

    create_relation = Relation.objects.create
    create_relation(subject_entity=document, type_id=REL_SUB_BILL_ISSUED,    object_entity=opp.get_source(), user=user)
    create_relation(subject_entity=document, type_id=REL_SUB_BILL_RECEIVED,  object_entity=opp.get_target(), user=user)
    create_relation(subject_entity=opp,      type_id=_RELATIONS_DICT[klass], object_entity=document,         user=user)

    document.generate_number() #Need the relation with emitter orga
    document.name = u'%s(%s)' % (document.number, opp.name)
    document.save()

    relations = Relation.objects.filter(subject_entity=opp, type__in=[REL_OBJ_LINKED_PRODUCT, REL_OBJ_LINKED_SERVICE]).select_related('object_entity')
    Relation.populate_real_object_entities(relations)

    for relation in relations:
        item = relation.object_entity.get_real_entity()
        line_klass = ProductLine if isinstance(item, Product) else ServiceLine
        line_klass.objects.create(related_item=item,
                                  related_document=document,
                                  unit_price=item.unit_price,
                                  vat_value=Vat.get_default_vat())

    for relation in Relation.objects.filter(object_entity=opp.id, type=REL_SUB_CURRENT_DOC, subject_entity__entity_type=ct_doc):
        relation.delete()

    if _CURRENT_DOC_DICT[klass]:
        create_relation(subject_entity=document, type_id=REL_SUB_CURRENT_DOC, object_entity=opp, user=user)
        if opp.use_current_quote:
            opp.update_estimated_sales(document)

    workflow_action = _WORKFLOW_DICT[klass]
    if workflow_action:
        workflow_action(opp.get_source(), opp.get_target(), user)

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")

    return HttpResponseRedirect(opp.get_absolute_url())
