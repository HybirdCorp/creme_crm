################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from django.utils.translation import gettext_lazy as _

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.views import generic

from ... import billing
from .. import custom_forms
from ..constants import DEFAULT_HFILTER_QUOTE
from . import base

Quote = billing.get_quote_model()
Invoice = billing.get_invoice_model()
SalesOrder = billing.get_sales_order_model()


class QuoteCreation(generic.EntityCreation):
    model = Quote
    form_class = custom_forms.QUOTE_CREATION_CFORM


class RelatedQuoteCreation(base.RelatedBaseCreation):
    model = Quote
    form_class = custom_forms.QUOTE_CREATION_CFORM
    permissions = ('billing', cperm(Quote))
    title = _('Create a quote for «{entity}»')


class QuoteDetail(generic.EntityDetail):
    model = Quote
    template_name = 'billing/view_quote.html'
    pk_url_kwarg = 'quote_id'


class QuoteEdition(generic.EntityEdition):
    model = Quote
    form_class = custom_forms.QUOTE_EDITION_CFORM
    pk_url_kwarg = 'quote_id'


class QuotesList(base.BaseList):
    model = Quote
    default_headerfilter_id = DEFAULT_HFILTER_QUOTE
