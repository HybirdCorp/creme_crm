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

from django.utils.translation import gettext_lazy as _

from creme.creme_core.views import generic

from .. import get_address_model
from ..forms import address as address_forms

Address = get_address_model()


class AddressCreation(generic.AddingInstanceToEntityPopup):
    model = Address
    form_class = address_forms.AddressForm
    permissions = 'persons'
    title = _('Adding address to «{entity}»')


class BillingAddressCreation(AddressCreation):
    form_class = address_forms.BillingAddressForm
    title = _('Adding billing address to «{entity}»')


class ShippingAddressCreation(AddressCreation):
    form_class = address_forms.ShippingAddressForm
    title = _('Adding shipping address to «{entity}»')


class AddressEdition(generic.RelatedToEntityEditionPopup):
    model = Address
    form_class = address_forms.AddressForm
    pk_url_kwarg = 'address_id'
    permissions = 'persons'

    form_classes = {
        'billing':  address_forms.BillingAddressForm,
        'shipping': address_forms.ShippingAddressForm,
    }

    default_title_format = _('Edit address for «{entity}»')
    title_formats = {
        'billing':  _('Edit billing address for «{entity}»'),
        'shipping': _('Edit shipping address for «{entity}»'),
    }

    def get_address_type(self):
        return self.request.GET.get('type')

    def get_form_class(self):
        return self.form_classes.get(self.get_address_type()) or super().get_form_class()

    @property
    def title(self):
        return self.title_formats.get(self.get_address_type(), self.default_title_format)
