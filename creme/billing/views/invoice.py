# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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

from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views.decorators import POST_only
from creme.creme_core.views.generic import (add_entity, edit_entity, list_view,
        view_entity)

from .. import get_invoice_model
from ..constants import (DEFAULT_INVOICE_STATUS, DEFAULT_DRAFT_INVOICE_STATUS,
         DEFAULT_HFILTER_INVOICE)
from ..forms.invoice import InvoiceCreateForm, InvoiceEditForm
from ..models import InvoiceStatus
from ..views.workflow import generic_add_related


Invoice = get_invoice_model()


def abstract_add_invoice(request, form=InvoiceCreateForm,
                         initial_status=DEFAULT_DRAFT_INVOICE_STATUS,
                         # submit_label=_(u'Save the invoice'),
                         submit_label=Invoice.save_label,
                        ):
    return add_entity(request, form,
                      extra_initial={'status': initial_status},
                      extra_template_dict={'submit_label': submit_label},
                     )


def abstract_add_related_invoice(request, target_id, form=InvoiceCreateForm,
                                 initial_status=DEFAULT_DRAFT_INVOICE_STATUS,
                                 title=_(u'Create an invoice for «%s»'),
                                 # submit_label=_(u'Save the invoice'),
                                 submit_label=Invoice.save_label,
                                ):
    return generic_add_related(request, target_id=target_id,
                               form=form, title=title,
                               submit_label=submit_label,
                               status_id=initial_status,
                              )


def abstract_edit_invoice(request, invoice_id, form=InvoiceEditForm):
    return edit_entity(request, invoice_id, Invoice, form)


def abstract_view_invoice(request, invoice_id, template='billing/view_billing.html'):
    return view_entity(request, invoice_id, Invoice,
                       template=template, extra_template_dict={'can_download': True},
                      )


@login_required
@permission_required(('billing', cperm(Invoice)))
def add(request):
    return abstract_add_invoice(request)


@login_required
@permission_required(('billing', cperm(Invoice)))
def add_related(request, target_id):
   return abstract_add_related_invoice(request, target_id)


@login_required
@permission_required('billing')
def edit(request, invoice_id):
    return abstract_edit_invoice(request, invoice_id)


@login_required
@permission_required('billing')
def detailview(request, invoice_id):
    return abstract_view_invoice(request, invoice_id)


@login_required
@permission_required('billing')
def listview(request):
    return list_view(request, Invoice, hf_pk=DEFAULT_HFILTER_INVOICE)


@login_required
@permission_required('billing')
@POST_only
def generate_number(request, invoice_id):
    invoice = get_object_or_404(Invoice, pk=invoice_id)

    request.user.has_perm_to_change_or_die(invoice)

    # TODO: move in model ???
    if not invoice.number:
        status = get_object_or_404(InvoiceStatus, pk=DEFAULT_INVOICE_STATUS)

        invoice.generate_number()
        invoice.status = status

        if not invoice.issuing_date:
            invoice.issuing_date = date.today()

        invoice.save()
    else:
        raise Http404('This invoice has already a number: %s.' % invoice)

    return HttpResponse('', content_type='text/javascript')
