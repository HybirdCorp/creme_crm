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

from datetime import datetime
from itertools import chain

from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required, permission_required

from creme_core.models import Relation
from creme_core.views.generic import add_entity, edit_entity, view_entity, list_view
from creme_core.utils import get_ct_or_404

from persons.models import Organisation

from documents.constants import REL_SUB_CURRENT_DOC

from billing.models import Quote, Invoice, SalesOrder
from billing.constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED

from opportunities.models import Opportunity
from opportunities.forms.opportunity import OpportunityCreateForm, OpportunityEditForm
from opportunities.constants import REL_OBJ_LINKED_QUOTE, REL_OBJ_LINKED_INVOICE, REL_OBJ_LINKED_SALESORDER


@login_required
@permission_required('opportunities')
@permission_required('opportunities.add_opportunity')
def add(request):
    return add_entity(request, OpportunityCreateForm)

@login_required
@permission_required('opportunities')
@permission_required('opportunities.add_opportunity')
def add_to_orga(request, orga_id):
    orga = get_object_or_404(Organisation, pk=orga_id)
    orga.can_link_or_die(request.user) #TODO: test the link creds with the future opp in the form.clean()

    return add_entity(request, OpportunityCreateForm, extra_initial={"target_orga": orga_id})

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

    document = klass.objects.create(user=user, issuing_date=datetime.now(), status_id=1,
                                    comment=_(u"Generated from the opportunity «%s»") % opp
                                   )

    create_relation = Relation.objects.create
    create_relation(subject_entity=document, type_id=REL_SUB_BILL_ISSUED,    object_entity=opp.get_emit_orga(),   user=user)
    create_relation(subject_entity=document, type_id=REL_SUB_BILL_RECEIVED,  object_entity=opp.get_target_orga(), user=user)
    create_relation(subject_entity=opp,      type_id=_RELATIONS_DICT[klass], object_entity=document,              user=user)

    document.generate_number() #Need the relation with emitter orga
    document.name = u'%s(%s)' % (document.number, opp.name)
    document.save()

    for line in chain(opp.product_lines, opp.service_lines):
        new_line = line.clone()
        new_line.document = document
        new_line.save()

    for relation in Relation.objects.filter(object_entity=opp.id, type=REL_SUB_CURRENT_DOC, subject_entity__entity_type=ct_doc):
        relation.delete()

    if _CURRENT_DOC_DICT[klass]:
        create_relation(subject_entity=document, type_id=REL_SUB_CURRENT_DOC, object_entity=opp, user=user)

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")

    return HttpResponseRedirect(opp.get_absolute_url())
