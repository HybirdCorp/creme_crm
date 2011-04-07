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

from django.contrib.auth.decorators import login_required, permission_required
from django.http import Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.utils.translation import ugettext_lazy as _
from creme_core.utils import jsonify

from creme_core.views.generic.add import add_to_entity
from creme_core.views.generic.edit import edit_related_to_entity

from billing.forms.payment_information import PaymentInformationCreateForm, PaymentInformationEditForm
from billing.models.other_models import PaymentInformation
from billing.models import Base


@login_required
@permission_required('billing')
def add(request, entity_id):
    return add_to_entity(request, entity_id, PaymentInformationCreateForm, _(u"New payment information in the organisation <%s>"))

@login_required
@permission_required('billing')
def edit(request, payment_information_id):
    return edit_related_to_entity(request, payment_information_id, PaymentInformation, PaymentInformationEditForm, _(u"Payment information for <%s>"))

@jsonify
@login_required
@permission_required('billing')
def set_default(request, payment_information_id, billing_id):
    pi      = get_object_or_404(PaymentInformation, pk=payment_information_id)
    billing_doc = get_object_or_404(Base, pk=billing_id)
    user    = request.user

    organisation = pi.get_related_entity()
    organisation.can_view_or_die(user)

    billing_doc.can_change_or_die(user)

    inv_orga_source = billing_doc.get_source().get_real_entity()
    if not inv_orga_source or inv_orga_source != organisation:
        raise Http404('No organisation in this invoice.')

    billing_doc.payment_info = pi
    billing_doc.save()
    
    return {}

