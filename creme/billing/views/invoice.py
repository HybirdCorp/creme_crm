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

from datetime import date

from django.http import HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.translation import ugettext as _

from creme_core.models import CremeEntity
from creme_core.views.generic import add_entity, edit_entity, list_view, view_entity, add_model_with_popup

from billing.models import Invoice, InvoiceStatus
from billing.views.workflow import _add_with_relations
from billing.forms.invoice import InvoiceCreateForm, InvoiceEditForm
from billing.constants import DEFAULT_INVOICE_STATUS, DEFAULT_DRAFT_INVOICE_STATUS


@login_required
@permission_required('billing')
@permission_required('billing.add_invoice')
def add(request):
    return add_entity(request, InvoiceCreateForm, extra_initial={'status': DEFAULT_DRAFT_INVOICE_STATUS})

@login_required
@permission_required('billing')
@permission_required('billing.add_invoice')
def add_from_detailview(request, entity_id):
    entity = get_object_or_404(CremeEntity, pk=entity_id).get_real_entity()
    entity.can_change_or_die(request.user)

    return add_model_with_popup(request, InvoiceCreateForm,
                                title=_(u"Add an invoice for <%s>") % entity,
                                initial={'target': entity, 'status': DEFAULT_DRAFT_INVOICE_STATUS}
                               )

@login_required
@permission_required('billing')
@permission_required('billing.add_invoice')
def add_with_relations(request, target_id, source_id):
    return _add_with_relations(request, target_id, source_id, InvoiceCreateForm,
                               _(u"Add an invoice for <%s>"), status_id=DEFAULT_DRAFT_INVOICE_STATUS,
                              )

@login_required
@permission_required('billing')
def edit(request, invoice_id):
    return edit_entity(request, invoice_id, Invoice, InvoiceEditForm)

@login_required
@permission_required('billing')
def detailview(request, invoice_id):
    return view_entity(request, invoice_id, Invoice, '/billing/invoice',
                       'billing/view_billing.html', {'can_download': True},
                      )

@login_required
@permission_required('billing')
def listview(request):
    return list_view(request, Invoice, extra_dict={'add_url': '/billing/invoice/add'})

@login_required
@permission_required('billing')
def generate_number(request, invoice_id):
    if request.method != 'POST':
        raise Http404('This view uses POST method.')

    invoice = get_object_or_404(Invoice, pk=invoice_id)

    invoice.can_change_or_die(request.user)

    #TODO: move in model ???
    if not invoice.number:
        status = get_object_or_404(InvoiceStatus, pk=DEFAULT_INVOICE_STATUS)

        invoice.generate_number()
        invoice.status = status

        if not invoice.issuing_date:
            invoice.issuing_date = date.today()

        invoice.save()
    else:
        raise Http404('This invoice has already a number: %s.' % invoice)

    return HttpResponseRedirect(invoice.get_absolute_url())
