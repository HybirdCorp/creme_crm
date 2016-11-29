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

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views.generic import add_entity, edit_entity, list_view, view_entity

from .. import get_quote_model, get_invoice_model, get_sales_order_model
from ..constants import DEFAULT_HFILTER_QUOTE
from ..forms.quote import QuoteCreateForm, QuoteEditForm
from ..views.workflow import generic_add_related


Quote = get_quote_model()
Invoice = get_invoice_model()
SalesOrder = get_sales_order_model()


def abstract_add_quote(request, form=QuoteCreateForm,
                       initial_status=1,
                       # submit_label=_('Save the quote'),
                       submit_label=Quote.save_label,
                      ):
    return add_entity(request, form, extra_initial={'status': initial_status},
                      extra_template_dict={'submit_label': submit_label},
                     )


def abstract_add_related_quote(request, target_id, form=QuoteCreateForm,
                               initial_status=1,
                               title=_(u'Create a quote for «%s»'),
                               # submit_label=_(u'Save the quote')
                               submit_label=Quote.save_label,
                              ):
    return generic_add_related(request, target_id, form=form,
                               title=title, status_id=initial_status,
                               submit_label=submit_label,
                              )


def abstract_edit(request, quote_id, form=QuoteEditForm):
    return edit_entity(request, quote_id, Quote, form)


def abstract_view_quote(request, quote_id, template='billing/view_quote.html'):
    user = request.user
    has_perm = user.has_perm
    isnt_staff = not user.is_staff

    return view_entity(request, quote_id, Quote,
                       template=template,
                       extra_template_dict={
                            'can_download':       True,
                            'can_create_order':   has_perm(cperm(SalesOrder)) and isnt_staff,
                            'can_create_invoice': has_perm(cperm(Invoice)) and isnt_staff,
                       },
                      )


@login_required
@permission_required(('billing', cperm(Quote)))
def add(request):
    return abstract_add_quote(request)


@login_required
@permission_required(('billing', cperm(Quote)))
def add_related(request, target_id):
    return abstract_add_related_quote(request, target_id)


@login_required
@permission_required('billing')
def edit(request, quote_id):
    return abstract_edit(request, quote_id)


@login_required
@permission_required('billing')
def detailview(request, quote_id):
    return abstract_view_quote(request, quote_id)


@login_required
@permission_required('billing')
def listview(request):
    return list_view(request, Quote, hf_pk=DEFAULT_HFILTER_QUOTE)
