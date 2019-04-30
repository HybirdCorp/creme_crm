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
# import warnings

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

# def abstract_add_invoice(request, form=invoice_forms.InvoiceCreateForm,
#                          initial_status=constants.DEFAULT_DRAFT_INVOICE_STATUS,
#                          submit_label=Invoice.save_label,
#                         ):
#     warnings.warn('billing.views.invoice.abstract_add_invoice() is deprecated ; '
#                   'use the class-based view InvoiceCreation instead.',
#                   DeprecationWarning
#                  )
#     return generic.add_entity(request, form,
#                               extra_initial={'status': initial_status},
#                               extra_template_dict={'submit_label': submit_label},
#                              )


# def abstract_add_related_invoice(request, target_id, form=invoice_forms.InvoiceCreateForm,
#                                  initial_status=constants.DEFAULT_DRAFT_INVOICE_STATUS,
#                                  title=_(u'Create an invoice for «%s»'),
#                                  submit_label=Invoice.save_label,
#                                 ):
#     from ..views.workflow import generic_add_related
#
#     return generic_add_related(request, target_id=target_id,
#                                form=form, title=title,
#                                submit_label=submit_label,
#                                status_id=initial_status,
#                               )


# def abstract_edit_invoice(request, invoice_id, form=invoice_forms.InvoiceEditForm):
#     warnings.warn('billing.views.invoice.abstract_edit_invoice() is deprecated ; '
#                   'use the class-based view InvoiceEdition instead.',
#                   DeprecationWarning
#                  )
#     return generic.edit_entity(request, invoice_id, Invoice, form)


# def abstract_view_invoice(request, invoice_id, template='billing/view_invoice.html'):
#     warnings.warn('billing.views.invoice.abstract_view_invoice() is deprecated ; '
#                   'use the class-based view InvoiceDetail instead.',
#                   DeprecationWarning
#                  )
#     return generic.view_entity(request, invoice_id, Invoice,
#                                template=template,
#                               )


# @login_required
# @permission_required(('billing', cperm(Invoice)))
# def add(request):
#     warnings.warn('billing.views.invoice.add() is deprecated.', DeprecationWarning)
#     return abstract_add_invoice(request)


# @login_required
# @permission_required(('billing', cperm(Invoice)))
# def add_related(request, target_id):
#    return abstract_add_related_invoice(request, target_id)


# @login_required
# @permission_required('billing')
# def edit(request, invoice_id):
#     warnings.warn('billing.views.invoice.edit() is deprecated.', DeprecationWarning)
#     return abstract_edit_invoice(request, invoice_id)


# @login_required
# @permission_required('billing')
# def detailview(request, invoice_id):
#     warnings.warn('billing.views.invoice.detailview() is deprecated.', DeprecationWarning)
#     return abstract_view_invoice(request, invoice_id)


# @login_required
# @permission_required('billing')
# def listview(request):
#     return generic.list_view(request, Invoice, hf_pk=constants.DEFAULT_HFILTER_INVOICE)


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


class InvoiceEdition(generic.EntityEdition):
    model = Invoice
    form_class = invoice_forms.InvoiceEditForm
    template_name = 'persons/edit_organisation_form.html'
    pk_url_kwarg = 'invoice_id'


class InvoicesList(generic.EntitiesList):
    model = Invoice
    default_headerfilter_id = constants.DEFAULT_HFILTER_INVOICE
