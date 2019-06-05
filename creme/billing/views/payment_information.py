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

from django.db.transaction import atomic
from django.http import HttpResponse  # Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

# from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import FieldsConfig  # CremeEntity
from creme.creme_core.views import generic  # decorators
# from creme.creme_core.views.decorators import jsonify

from creme.persons import get_organisation_model

from ... import billing

from ..forms import payment_information as pi_forms
from ..models import PaymentInformation


class PaymentInformationCreation(generic.AddingInstanceToEntityPopup):
    model = PaymentInformation
    form_class = pi_forms.PaymentInformationCreateForm
    permissions = 'billing'
    entity_id_url_kwarg = 'orga_id'
    entity_classes = get_organisation_model()
    title = _('New payment information in the organisation «{entity}»')


class PaymentInformationEdition(generic.RelatedToEntityEditionPopup):
    model = PaymentInformation
    form_class = pi_forms.PaymentInformationEditForm
    permissions = 'billing'
    pk_url_kwarg = 'pinfo_id'
    title = _('Payment information for «{entity}»')


# @jsonify
# @login_required
# @permission_required('billing')
# @decorators.POST_only
# @atomic
# def set_default(request, payment_information_id, billing_id):
#     pi = get_object_or_404(PaymentInformation, pk=payment_information_id)
#     entity = get_object_or_404(CremeEntity.objects.select_for_update(), pk=billing_id)
#     user = request.user
#
#     real_model = entity.entity_type.model_class()
#
#     if real_model not in {billing.get_invoice_model(),
#                           billing.get_quote_model(),
#                           billing.get_sales_order_model(),
#                           billing.get_credit_note_model(),
#                           billing.get_template_base_model(),
#                          }:
#         raise Http404('This entity is not a billing document')
#
#     if FieldsConfig.get_4_model(real_model).is_fieldname_hidden('payment_info'):
#         raise ConflictError('The field "payment_info" is hidden.')
#
#     billing_doc = entity.get_real_entity()
#
#     organisation = pi.get_related_entity()
#     user.has_perm_to_view_or_die(organisation)
#     user.has_perm_to_link_or_die(organisation)
#
#     user.has_perm_to_change_or_die(billing_doc)
#
#     inv_orga_source = billing_doc.get_source()
#     if not inv_orga_source or inv_orga_source.id != organisation.id:
#         raise Http404('No organisation in this invoice.')
#
#     billing_doc.payment_info = pi
#     billing_doc.save()
#
#     return {}
class PaymentInformationAsDefault(generic.base.EntityRelatedMixin, generic.CheckedView):
    permissions = 'billing'
    entity_classes = [
        billing.get_invoice_model(),
        billing.get_quote_model(),
        billing.get_sales_order_model(),
        billing.get_credit_note_model(),
        billing.get_template_base_model(),
    ]
    entity_select_for_update = True

    payment_info_id_url_kwarg = 'pinfo_id'
    payment_info_fk = 'payment_info'

    def get_payment_information(self):
        return get_object_or_404(
            PaymentInformation,
            pk=self.kwargs[self.payment_info_id_url_kwarg],
        )

    @atomic
    def post(self, request, *args, **kwargs):
        pi = self.get_payment_information()
        billing_doc = self.get_related_entity()

        if FieldsConfig.get_4_model(type(billing_doc))\
                       .is_fieldname_hidden(self.payment_info_fk):
            raise ConflictError('The field "{}" is hidden.'.format(self.payment_info_fk))

        user = request.user
        organisation = pi.get_related_entity()
        user.has_perm_to_view_or_die(organisation)
        user.has_perm_to_link_or_die(organisation)

        source = billing_doc.get_source()
        if not source or source.id != organisation.id:
            raise ConflictError('The related organisation does not match.')

        billing_doc.payment_info = pi
        billing_doc.save()

        return HttpResponse()
