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

import datetime

from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect, Http404
from django.contrib.auth.decorators import login_required, permission_required

from creme_core.views.generic import add_entity, edit_entity, list_view

from billing.constants import DEFAULT_INVOICE_STATUS
from billing.models import Invoice, InvoiceStatus
from billing.forms.invoice import InvoiceCreateForm, InvoiceEditForm
from billing.views.base import view_billing_entity


@login_required
@permission_required('billing')
@permission_required('billing.add_invoice')
def add(request):
    return add_entity(request, InvoiceCreateForm)

def edit(request, invoice_id):
    return edit_entity(request, invoice_id, Invoice, InvoiceEditForm, 'billing')

@login_required
@permission_required('billing')
def detailview(request, invoice_id):
    invoice = get_object_or_404(Invoice, pk=invoice_id)
    return view_billing_entity(request, invoice, '/billing/invoice')

@login_required
@permission_required('billing')
def listview(request):
    return list_view(request, Invoice, extra_dict={'add_url': '/billing/invoice/add'})

@login_required
@permission_required('billing')
def generate_number(request, invoice_id):
    invoice = get_object_or_404(Invoice, pk=invoice_id)

    #TODO: edit credentials ??

    if not invoice.number:
        status = get_object_or_404(InvoiceStatus, pk=DEFAULT_INVOICE_STATUS)

        invoice.generate_number()
        invoice.status = status

        if not invoice.issuing_date:
            invoice.issuing_date = datetime.now()

        invoice.save()

    return HttpResponseRedirect(invoice.get_absolute_url())
