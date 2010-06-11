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

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType

from creme_core.entities_access.functions_for_permissions import add_view_or_die, get_view_or_die
from creme_core.views.generic import add_entity, edit_entity, list_view

from billing.models import Invoice
from billing.forms.invoice import InvoiceCreateForm, InvoiceEditForm
from billing.views.base import view_billing_entity


@login_required
@get_view_or_die('billing')
@add_view_or_die(ContentType.objects.get_for_model(Invoice), None, 'billing')
def add(request):
    return add_entity(request, InvoiceCreateForm, template='billing/add_billing.html')

def edit(request, invoice_id):
    return edit_entity(request, invoice_id, Invoice, InvoiceEditForm, 'billing', 'billing/edit_billing.html')

@login_required
def detailview(request, invoice_id):
    invoice = get_object_or_404(Invoice, pk=invoice_id)
    return view_billing_entity(request, invoice_id, invoice, '/billing/invoice')

@login_required
@get_view_or_die('billing')
def listview(request):
    return list_view(request, Invoice, extra_dict={'add_url':'/billing/invoice/add'})
