# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

import warnings

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.views import generic
from creme.creme_core.auth.decorators import login_required, permission_required

from ... import billing

from ..constants import DEFAULT_HFILTER_QUOTE
from ..forms import quote as quote_forms

from . import base

Quote = billing.get_quote_model()
Invoice = billing.get_invoice_model()
SalesOrder = billing.get_sales_order_model()

# Function views --------------------------------------------------------------


def abstract_add_quote(request, form=quote_forms.QuoteCreateForm,
                       initial_status=1,
                       submit_label=Quote.save_label,
                      ):
    warnings.warn('billing.views.quote.abstract_view_quote() is deprecated ; '
                  'use the class-based view QuoteCreation instead.',
                  DeprecationWarning
                 )
    return generic.add_entity(request, form, extra_initial={'status': initial_status},
                              extra_template_dict={'submit_label': submit_label},
                             )


def abstract_add_related_quote(request, target_id, form=quote_forms.QuoteCreateForm,
                               initial_status=1,
                               title=_('Create a quote for «%s»'),
                               submit_label=Quote.save_label,
                              ):
    warnings.warn('billing.views.quote.abstract_add_related_quote() is deprecated ; '
                  'use the class-based view RelatedQuoteCreation instead.',
                  DeprecationWarning
                 )
    from ..views.workflow import generic_add_related

    return generic_add_related(request, target_id, form=form,
                               title=title, status_id=initial_status,
                               submit_label=submit_label,
                              )


def abstract_edit(request, quote_id, form=quote_forms.QuoteEditForm):
    warnings.warn('billing.views.quote.abstract_edit_quote() is deprecated ; '
                  'use the class-based view QuoteEdition instead.',
                  DeprecationWarning
                 )
    return generic.edit_entity(request, quote_id, Quote, form)


def abstract_view_quote(request, quote_id, template='billing/view_quote.html'):
    warnings.warn('billing.views.quote.abstract_view_quote() is deprecated ; '
                  'use the class-based view QuoteDetail instead.',
                  DeprecationWarning
                 )

    user = request.user
    has_perm = user.has_perm
    isnt_staff = not user.is_staff

    return generic.view_entity(request, quote_id, Quote,
                               template=template,
                               extra_template_dict={
                                    'can_create_order':   has_perm(cperm(SalesOrder)) and isnt_staff,
                                    'can_create_invoice': has_perm(cperm(Invoice)) and isnt_staff,
                               },
                              )


@login_required
@permission_required(('billing', cperm(Quote)))
def add(request):
    warnings.warn('billing.views.quote.add() is deprecated.', DeprecationWarning)
    return abstract_add_quote(request)


@login_required
@permission_required(('billing', cperm(Quote)))
def add_related(request, target_id):
    warnings.warn('billing.views.quote.add_related() is deprecated.', DeprecationWarning)
    return abstract_add_related_quote(request, target_id)


@login_required
@permission_required('billing')
def edit(request, quote_id):
    warnings.warn('billing.views.quote.edit() is deprecated.', DeprecationWarning)
    return abstract_edit(request, quote_id)


@login_required
@permission_required('billing')
def detailview(request, quote_id):
    warnings.warn('billing.views.quote.detailview() is deprecated.', DeprecationWarning)
    return abstract_view_quote(request, quote_id)


@login_required
@permission_required('billing')
def listview(request):
    return generic.list_view(request, Quote, hf_pk=DEFAULT_HFILTER_QUOTE)


# Class-based views  ----------------------------------------------------------

class QuoteCreation(base.BaseCreation):
    model = Quote
    form_class = quote_forms.QuoteCreateForm


class RelatedQuoteCreation(base.RelatedBaseCreation):
    model = Quote
    form_class = quote_forms.QuoteCreateForm
    permissions = ('billing', cperm(Quote))
    title_format = _('Create a quote for «{}»')


class QuoteDetail(generic.EntityDetail):
    model = Quote
    template_name = 'billing/view_quote.html'
    pk_url_kwarg = 'quote_id'


class QuoteEdition(generic.EntityEdition):
    model = Quote
    form_class = quote_forms.QuoteEditForm
    pk_url_kwarg = 'quote_id'
