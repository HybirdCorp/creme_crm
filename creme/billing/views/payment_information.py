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

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import CremeEntity, FieldsConfig
from creme.creme_core.utils import jsonify
from creme.creme_core.views import generic, decorators

from creme.persons import get_organisation_model

from ... import billing
from ..forms import payment_information as pi_forms
from ..models import PaymentInformation


# @login_required
# @permission_required('billing')
# def add(request, entity_id):
#     return generic.add_to_entity(request, entity_id, pi_forms.PaymentInformationCreateForm,
#                                  _('New payment information in the organisation «%s»'),
#                                  entity_class=get_organisation_model(),
#                                  submit_label=_('Save the payment information'),
#                                 )
class PaymentInformationCreation(generic.AddingToEntity):
    model = PaymentInformation
    form_class = pi_forms.PaymentInformationCreateForm
    permissions = 'billing'
    entity_id_url_kwarg = 'orga_id'
    entity_classes = get_organisation_model()
    title_format = _('New payment information in the organisation «{}»')


# @login_required
# @permission_required('billing')
# def edit(request, payment_information_id):
#     return generic.edit_related_to_entity(request, payment_information_id,
#                                           PaymentInformation, pi_forms.PaymentInformationEditForm,
#                                           _('Payment information for «%s»'),
#                                          )
class PaymentInformationEdition(generic.RelatedToEntityEdition):
    model = PaymentInformation
    form_class = pi_forms.PaymentInformationEditForm
    permissions = 'billing'
    pk_url_kwarg = 'pinfo_id'
    title_format = _('Payment information for «{}»')


@jsonify
@login_required
@permission_required('billing')
@decorators.POST_only
def set_default(request, payment_information_id, billing_id):
    pi = get_object_or_404(PaymentInformation, pk=payment_information_id)
    billing_doc = get_object_or_404(CremeEntity, pk=billing_id).get_real_entity()
    user = request.user

    if not isinstance(billing_doc, (billing.get_invoice_model(), billing.get_quote_model(),
                                    billing.get_sales_order_model(), billing.get_credit_note_model(),
                                    billing.get_template_base_model(),
                                   )
                     ):
        raise Http404('This entity is not a billing document')

    if FieldsConfig.get_4_model(billing_doc.__class__).is_fieldname_hidden('payment_info'):
        raise ConflictError('The field "payment_info" is hidden.')

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
