# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from django.contrib.auth.decorators import login_required, permission_required
from django.utils.translation import ugettext as _

from creme.creme_core.views.generic import add_entity, edit_entity, list_view, view_entity

from creme.billing.models import Quote
from creme.billing.views.workflow import _add_with_relations
from creme.billing.forms.quote import QuoteCreateForm, QuoteEditForm


@login_required
@permission_required('billing')
@permission_required('billing.add_quote')
def add(request):
    return add_entity(request, QuoteCreateForm, extra_initial={'status': 1})

@login_required
@permission_required('billing')
@permission_required('billing.add_quote')
def add_with_relations(request, target_id, source_id):
    return _add_with_relations(request, target_id, source_id, QuoteCreateForm,
                               _(u"Add a quote for <%s>"), status_id=1
                              )

@login_required
@permission_required('billing')
def edit(request, quote_id):
    return edit_entity(request, quote_id, Quote, QuoteEditForm)

@login_required
@permission_required('billing')
def detailview(request, quote_id):
    has_perm = request.user.has_perm

    return view_entity(request, quote_id, Quote, '/billing/quote',
                       'billing/view_quote.html',
                       {'can_download':       True,
                        'can_create_order':   has_perm('billing.add_salesorder'),
                        'can_create_invoice': has_perm('billing.add_invoice'),
                       },
                      )

@login_required
@permission_required('billing')
def listview(request):
    return list_view(request, Quote, extra_dict={'add_url': '/billing/quote/add'})
