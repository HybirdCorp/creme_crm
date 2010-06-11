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


from decimal import Decimal

from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.contrib.auth.decorators import login_required

from creme_core.models.entity import CremeEntity
from creme_core.entities_access.functions_for_permissions import edit_object_or_die, get_view_or_die


from creme_core.utils import jsonify

from billing.models import Line, ProductLine, ServiceLine

from billing.constants import DEFAULT_VAT

from opportunities.blocks import linked_product_lines_block, linked_service_lines_block
from billing.blocks import total_block
default_decimal = Decimal()



def _edit_line (request, line , document, form_class):
    if request.POST :
        line_form = form_class(request.POST,instance=line)
        

        if line_form.is_valid():
            line_form.save()


            return render_to_response('creme_core/generics/nothing.html', {}, context_instance=RequestContext(request))
        else:
            pass
            #print line_form.errors
    else:
        line_form = form_class(initial={'document_id': document.id} ,instance=line)


    return render_to_response('creme_core/generics/blockform/add_popup.html',
                              {
                                'form':   line_form,
                                'object': document,
                                'title':  u"Edition d'une ligne de commande dans le document <%s>" % document,
                              },
                              context_instance=RequestContext(request))    
    

@login_required
@get_view_or_die('billing')
def edit_productline(request, line_id):
    line      = get_object_or_404(ProductLine, pk=line_id)
    document  = line.document 
    die_status = edit_object_or_die(request, document, app_name='billing')
    if die_status:
        return die_status

    form_class = line.get_edit_form ()
    
    return _edit_line(request, line, document, form_class)

@login_required
@get_view_or_die('billing')
def edit_serviceline(request, line_id):
    line      = get_object_or_404(ServiceLine, pk=line_id)
    document  = line.document 
    die_status = edit_object_or_die(request, document, app_name='billing')
    if die_status:
        return die_status

    form_class = line.get_edit_form ()
    
    return _edit_line(request, line, document, form_class)


@login_required
@jsonify
def reload_product_lines(request, opp_id):
    context = {'request': request, 'object': CremeEntity.objects.get(id=opp_id).get_real_entity()}
    return [
            (linked_product_lines_block.id_, linked_product_lines_block.detailview_display(context)),
            (total_block.id_, total_block.detailview_display(context)),
           ]
        
    #return linked_product_lines_block.detailview_ajax(request, opp_id)

@login_required
@jsonify
def reload_service_lines(request, opp_id):
    context = {'request': request, 'object': CremeEntity.objects.get(id=opp_id).get_real_entity()}
    return [
            (linked_service_lines_block.id_, linked_service_lines_block.detailview_display(context)),
            (total_block.id_, total_block.detailview_display(context)),
           ]    
    #return linked_service_lines_block.detailview_ajax(request, opp_id)

