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
from logging import debug

from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required

from creme_core.models.entity import CremeEntity
from creme_core.entities_access.functions_for_permissions import edit_object_or_die, get_view_or_die
from creme_core.views.generic import add_to_entity, inner_popup
from creme_core.utils import get_from_POST_or_404

from billing.models import Line, ProductLine, ServiceLine
from billing.forms.line import ProductLineCreateForm, ProductLineOnTheFlyCreateForm, ServiceLineCreateForm, ServiceLineOnTheFlyCreateForm
from billing.constants import DEFAULT_VAT


default_decimal = Decimal()

def _add_line(request, form_class, document_id):
    return add_to_entity(request, document_id, form_class,
                         _(u"New line in the document <%s>"),
                         #initial={ #COMMENTED on 8 Oct 2010
                                    #'quantity':       0,
                                    #'unit_price':     default_decimal,
                                    #'credit':         default_decimal,
                                    #'discount':       default_decimal,
                                    #'total_discount': False,
                                    #'vat':            DEFAULT_VAT,
                                  #},
                         )

def add_product_line(request, document_id):
    return _add_line(request, ProductLineCreateForm, document_id)

def add_product_line_on_the_fly(request, document_id):
    return _add_line(request, ProductLineOnTheFlyCreateForm, document_id)

def add_service_line(request, document_id):
    return _add_line(request, ServiceLineCreateForm, document_id)

def add_service_line_on_the_fly(request, document_id):
    return _add_line(request, ServiceLineOnTheFlyCreateForm, document_id)

@login_required
@get_view_or_die('billing')
def _edit_line(request, line_model, line_id):
    line     = get_object_or_404(line_model, pk=line_id)
    document = line.document

    die_status = edit_object_or_die(request, document, app_name='billing')
    if die_status:
        return die_status

    form_class = line.get_edit_form()

    if request.POST:
        line_form = form_class(document, request.POST, instance=line)

        if line_form.is_valid():
            line_form.save()
    else:
        line_form = form_class(document, instance=line)

    return inner_popup(request, 'creme_core/generics/blockform/edit_popup.html',
                       {
                        'form':   line_form,
                        'title':  _(u"Edition of a line in the document <%s>") % document,
                       },
                       is_valid=line_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))

def edit_productline(request, line_id):
    return _edit_line(request, ProductLine, line_id)

def edit_serviceline(request, line_id):
    return _edit_line(request, ServiceLine, line_id)

@login_required
@get_view_or_die('billing')
def delete(request):
    line     = get_object_or_404(Line, pk=get_from_POST_or_404(request.POST, 'id'))
    document = line.document

    die_status = edit_object_or_die(request, document, app_name='billing')
    if die_status:
        return die_status

    line.delete()

#    return HttpResponseRedirect(document.get_absolute_url())
    return HttpResponse()

@login_required
@get_view_or_die('billing')
def update(request, line_id):
    line     = get_object_or_404(Line, pk=line_id)
    document = line.document

    die_status = edit_object_or_die(request, document, app_name='billing')
    if die_status:
        return die_status

    line.is_paid = request.POST.has_key('paid')
    line.save()

    return HttpResponseRedirect(document.get_absolute_url())
