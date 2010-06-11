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

from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect

from creme_core.entities_access.functions_for_permissions import add_view_or_die, get_view_or_die
from creme_core.views.generic import add_entity, edit_entity, view_entity_with_template, list_view
from creme_core.models import Relation

from persons.models import Organisation

from opportunities.models import Opportunity
from opportunities.forms.opportunity import OpportunityCreateForm, OpportunityEditForm

from billing.constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED
from documents.constants import REL_SUB_CURRENT_DOC
from opportunities.constants import REL_OBJ_LINKED_QUOTE, REL_OBJ_LINKED_INVOICE, REL_OBJ_LINKED_SALESORDER
from billing.models import Line, ProductLine , ServiceLine, Quote, Invoice, SalesOrder

from creme_config.models import CremeKVConfig 

_ct = ContentType.objects.get_for_model(Opportunity)


@login_required
@get_view_or_die('opportunities')
@add_view_or_die(_ct, None, 'opportunities')
def add(request):
    return add_entity(request, OpportunityCreateForm)

@login_required
@get_view_or_die('opportunities')
@add_view_or_die(_ct, None, 'opportunities')
def add_to_orga(request, orga_id):
    orga = get_object_or_404(Organisation, pk=orga_id)

    return add_entity(request, OpportunityCreateForm, extra_initial={"target_orga": orga_id})

def edit(request, opp_id):
    return edit_entity(request, opp_id, Opportunity, OpportunityEditForm, 'opportunities')

@login_required
@get_view_or_die('opportunities')
def detailview(request, opp_id):
    line_or_not = CremeKVConfig.objects.get(id="LINE_IN_OPPORTUNITIES").value
    return view_entity_with_template(request,
                                     opp_id,
                                     Opportunity,
                                     '/opportunities/opportunity',
                                     'opportunities/view_opportunity.html',
                                     {"line_or_not" : line_or_not})

@login_required
@get_view_or_die('opportunities')
def listview(request):
    return list_view(request, Opportunity, extra_dict={'add_url':'/opportunities/opportunity/add'})

@login_required
@get_view_or_die('opportunities')
def generate_new_doc(request, opp_id, ct_id ):
    
    dict_linked_rel = { Quote : REL_OBJ_LINKED_QUOTE , 
             Invoice : REL_OBJ_LINKED_INVOICE,
             SalesOrder : REL_OBJ_LINKED_SALESORDER
            }    
    
    dict_current_doc = { Quote : True , 
             Invoice : False,
             SalesOrder : False
            }     
    
    ct_doc = get_object_or_404 (ContentType,id=ct_id)
    opp = get_object_or_404 (Opportunity, id=opp_id)
    create_relation = Relation.create_relation_with_object
    klass = ct_doc.model_class ()
    document = klass ()
    document.user = opp.user
    document.name=opp.name 
    document.status_id = 1
    document.save () 
    
    create_relation(document, REL_SUB_BILL_ISSUED, opp.get_emit_orga())
    create_relation(document, REL_SUB_BILL_RECEIVED,opp.get_target_orga())

    create_relation(opp,dict_linked_rel[klass],document)
    
    lines = opp.LineDocumentRelation_set.all ()
    for line in lines : 
        try :
            src_line = line.productline
            new_line = src_line.clone ()
            new_line.document = document 
            new_line.save ()
            continue
        except :
            pass 
        try:
            src_line = line.serviceline
            new_line = src_line.clone ()
            new_line.document = document 
            new_line.save ()

        except :
            pass         
    
    for relation in Relation.objects.filter(object_id=opp_id, type=REL_SUB_CURRENT_DOC, subject_content_type=ct_doc):
        relation.delete()
    if dict_current_doc[klass]:
        create_relation(document, REL_SUB_CURRENT_DOC, opp)    
    return HttpResponseRedirect(opp.get_absolute_url())   