# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required, permission_required

from creme_core.utils import jsonify
from creme_core.views.generic import add_to_entity, list_view, edit_model_with_popup

from billing.models import Line, ProductLine, ServiceLine
from billing.forms.line import (ProductLineOnTheFlyForm, ServiceLineOnTheFlyForm, LineEditForm,
                                ProductLineMultipleAddForm, ServiceLineMultipleAddForm)


@login_required
@permission_required('billing')
def _add_line(request, form_class, document_id):
    return add_to_entity(request, document_id, form_class, _(u"New line in the document <%s>"))

@login_required
@permission_required('billing')
def add_multiple_product_line(request, document_id):
    return add_to_entity(request, document_id, ProductLineMultipleAddForm, _(u"Add one or more product to <%s>"), link_perm = True)

def add_product_line_on_the_fly(request, document_id):
    return _add_line(request, ProductLineOnTheFlyForm, document_id)

@login_required
@permission_required('billing')
def add_multiple_service_line(request, document_id):
    return add_to_entity(request, document_id, ServiceLineMultipleAddForm, _(u"Add one or more service to <%s>"), link_perm = True)

def add_service_line_on_the_fly(request, document_id):
    return _add_line(request, ServiceLineOnTheFlyForm, document_id)

def edit_line(request, line_id):
    return edit_model_with_popup(request, {'pk': line_id}, Line, LineEditForm)

@jsonify
@login_required
@permission_required('billing')
def edit_inner_line(request, line_id):
    if request.method != 'POST':
        raise Http404('This view uses POST method')

    line     = get_object_or_404(Line, pk=line_id)
    document = line.related_document

    document.can_change_or_die(request.user)

    request_POST = request.POST
    request_POST_get = request_POST.get

    # TODO try/catch in case POST values didnt match Decimal, int ?
    new_unit_price      = Decimal(request_POST_get('unit_price')) if 'unit_price' in request_POST else None
    new_quantity        = Decimal(request_POST_get('quantity'))   if 'quantity' in request_POST else None
    new_vat             = request_POST_get('vat')                 if 'vat' in request_POST else None
    new_discount_value  = Decimal(request_POST_get('discount'))   if 'discount' in request_POST else None
    new_discount_unit   = int(request_POST_get('discount_unit'))  if 'discount_unit' in request_POST else None
    new_unit            = request_POST_get('unit')                if 'unit' in request_POST else None

    if 'total_discount' in request_POST:
        new_discount_type = request_POST_get('total_discount') == '1'
    else:
        new_discount_type = None

    if not Line.is_discount_valid(new_unit_price if new_unit_price is not None else line.unit_price,
                                  new_quantity if new_quantity is not None else line.quantity,
                                  new_discount_value if new_discount_value is not None else line.discount,
                                  new_discount_unit if new_discount_unit is not None else line.discount_unit,
                                  new_discount_type if new_discount_type is not None else line.total_discount):
        # TODO Improve this functional error case by an error popup ?
        # For the moment data will always be verified by js functions so this server side validation is useless
        # return HttpResponse("", mimetype="text/javascript")
        return

    if new_unit_price is not None:
        line.unit_price = new_unit_price
    if new_quantity is not None:
        line.quantity = new_quantity
    if new_discount_value is not None:
        line.discount = new_discount_value
    if new_discount_unit is not None:
        line.discount_unit = new_discount_unit
    if new_discount_type is not None:
        line.total_discount = new_discount_type
    if new_vat is not None:
        line.vat_value_id = new_vat
    if new_unit is not None:
        line.unit = new_unit

    line.save()
    document.save()

@login_required
@permission_required('billing')
def listview(request):
    return list_view(request, Line, show_actions=False)

@login_required
@permission_required('billing')
def listview_product_line(request):
    return list_view(request, ProductLine, show_actions=False)

@login_required
@permission_required('billing')
def listview_service_line(request):
    return list_view(request, ServiceLine, show_actions=False)
