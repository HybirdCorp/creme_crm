# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import FieldsConfig
from creme.creme_core.views import generic
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


class PaymentInformationRelatedCreation(generic.AddingInstanceToEntityPopup):
    model = PaymentInformation
    form_class = pi_forms.PaymentInformationCreateForm
    permissions = 'billing'
    entity_classes = [
        billing.get_invoice_model(),
        billing.get_quote_model(),
        billing.get_sales_order_model(),
        billing.get_credit_note_model(),
        billing.get_template_base_model(),
    ]
    title = _('New payment information in the organisation «{entity}»')

    def check_related_entity_permissions(self, entity, user):
        super().check_related_entity_permissions(entity=entity, user=user)
        user.has_perm_to_change_or_die(entity.source)

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['entity'] = self.get_related_entity().source.allowed_str(self.request.user)

        return data

    def set_entity_in_form_kwargs(self, form_kwargs):
        entity = self.get_related_entity()

        if self.entity_form_kwarg:
            form_kwargs[self.entity_form_kwarg] = entity.source

    def form_valid(self, form):
        self.object = pi = form.save()

        entity = self.get_related_entity()
        entity.payment_info = pi
        entity.save()

        return HttpResponse(self.get_success_url(), content_type='text/plain')


class PaymentInformationEdition(generic.RelatedToEntityEditionPopup):
    model = PaymentInformation
    form_class = pi_forms.PaymentInformationEditForm
    permissions = 'billing'
    pk_url_kwarg = 'pinfo_id'
    title = _('Payment information for «{entity}»')


class PaymentInformationAsDefault(generic.base.EntityRelatedMixin, generic.CheckedView):
    permissions = 'billing'
    # TODO: factorise
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

        if FieldsConfig.objects.get_for_model(
            model=type(billing_doc),
        ).is_fieldname_hidden(self.payment_info_fk):
            raise ConflictError(f'The field "{self.payment_info_fk}" is hidden.')

        user = request.user
        organisation = pi.get_related_entity()
        user.has_perm_to_view_or_die(organisation)
        user.has_perm_to_link_or_die(organisation)

        source = billing_doc.source
        if not source or source.id != organisation.id:
            raise ConflictError('The related organisation does not match.')

        billing_doc.payment_info = pi
        billing_doc.save()

        return HttpResponse()
