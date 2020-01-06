# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

from datetime import date

from django.db.transaction import atomic
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views import generic, decorators

from .. import get_invoice_model, constants
from ..forms import invoice as invoice_forms
from ..models import InvoiceStatus

from . import base

Invoice = get_invoice_model()

# Function views --------------------------------------------------------------

@login_required
@permission_required('billing')
@decorators.POST_only
@atomic
def generate_number(request, invoice_id):
    invoice = get_object_or_404(Invoice.objects.select_for_update(), pk=invoice_id)

    request.user.has_perm_to_change_or_die(invoice)

    # TODO: move in model ???
    if not invoice.number:
        status = get_object_or_404(InvoiceStatus, pk=constants.DEFAULT_INVOICE_STATUS)

        invoice.generate_number()
        invoice.status = status

        if not invoice.issuing_date:
            invoice.issuing_date = date.today()

        invoice.save()
    else:
        raise Http404('This invoice has already a number: {}.'.format(invoice))

    return HttpResponse()


# Class-based views  ----------------------------------------------------------

class InvoiceCreation(base.BaseCreation):
    model = Invoice
    form_class = invoice_forms.InvoiceCreateForm
    initial_status = constants.DEFAULT_DRAFT_INVOICE_STATUS


class RelatedInvoiceCreation(base.RelatedBaseCreation):
    model = Invoice
    form_class = invoice_forms.InvoiceCreateForm
    permissions = ('billing', cperm(Invoice))
    title = _('Create an invoice for «{entity}»')
    initial_status = constants.DEFAULT_DRAFT_INVOICE_STATUS


class InvoiceDetail(generic.EntityDetail):
    model = Invoice
    template_name = 'billing/view_invoice.html'
    pk_url_kwarg = 'invoice_id'


class InvoiceEdition(base.BaseEdition):
    model = Invoice
    form_class = invoice_forms.InvoiceEditForm
    pk_url_kwarg = 'invoice_id'


class InvoicesList(generic.EntitiesList):
    model = Invoice
    default_headerfilter_id = constants.DEFAULT_HFILTER_INVOICE
