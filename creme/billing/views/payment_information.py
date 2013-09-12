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
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.views.generic import add_to_entity, edit_related_to_entity
from creme.creme_core.views.decorators import POST_only
from creme.creme_core.utils import jsonify

from creme.billing.models import Base, PaymentInformation
from creme.billing.forms.payment_information import PaymentInformationCreateForm, PaymentInformationEditForm


@login_required
@permission_required('billing')
def add(request, entity_id):
    return add_to_entity(request, entity_id, PaymentInformationCreateForm,
                         _(u"New payment information in the organisation <%s>"),
                        )

@login_required
@permission_required('billing')
def edit(request, payment_information_id):
    return edit_related_to_entity(request, payment_information_id,
                                  PaymentInformation, PaymentInformationEditForm,
                                  _(u"Payment information for <%s>"),
                                 )

@jsonify
@login_required
@permission_required('billing')
@POST_only
def set_default(request, payment_information_id, billing_id):
    pi      = get_object_or_404(PaymentInformation, pk=payment_information_id)
    billing_doc = get_object_or_404(Base, pk=billing_id)
    user    = request.user

    organisation = pi.get_related_entity()
    user.has_perm_to_view_or_die(organisation)
    user.has_perm_to_link_or_die(organisation)

    user.has_perm_to_change_or_die(billing_doc)

    inv_orga_source = billing_doc.get_source()
    if not inv_orga_source or inv_orga_source.id != organisation.id:
        raise Http404('No organisation in this invoice.')

    billing_doc.payment_info = pi
    billing_doc.save()

    return {}
