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

# import warnings

from django.utils.translation import gettext_lazy as _

# from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views import generic

from .. import get_address_model
from ..forms import address as address_forms

Address = get_address_model()


# Function views --------------------------------------------------------------

# def abstract_add_address(request, entity_id, form=address_forms.AddressForm,
#                          title=_('Adding address to «%s»'),
#                          submit_label=_('Save the address'),
#                         ):
#     warnings.warn('persons.views.address.abstract_add_address() is deprecated ;'
#                   'use the class AddressCreation instead.',
#                   DeprecationWarning
#                  )
#     return generic.add_to_entity(request, entity_id, form, title=title, submit_label=submit_label)


# def abstract_add_billing_address(request, entity_id, form=address_forms.BillingAddressForm,
#                                  title=_('Adding billing address to «%s»'),
#                                  submit_label=_('Save the address')
#                                 ):
#     warnings.warn('persons.views.address.abstract_add_billing_address() is deprecated ;'
#                   'use the class BillingAddressCreation instead.',
#                   DeprecationWarning
#                  )
#     return generic.add_to_entity(request, entity_id, form, title=title, submit_label=submit_label)


# def abstract_add_shipping_address(request, entity_id, form=address_forms.ShippingAddressForm,
#                                   title=_('Adding shipping address to «%s»'),
#                                   submit_label=_('Save the address'),
#                                 ):
#     warnings.warn('persons.views.address.abstract_add_shipping_address() is deprecated ;'
#                   'use the class BillingAddressCreation instead.',
#                   DeprecationWarning
#                  )
#     return generic.add_to_entity(request, entity_id, form, title=title, submit_label=submit_label)


# def abstract_edit_address(request, address_id, form=None, title=None):
#     warnings.warn('persons.views.address.abstract_edit_address() is deprecated ;'
#                   'use the class AddressEdition instead.',
#                   DeprecationWarning
#                  )
#
#     if form is None or title is None:
#         address_type = request.GET.get('type')
#
#         if address_type == 'billing':
#             title = _('Edit billing address for «%s»')
#             form = address_forms.BillingAddressForm
#         elif address_type == 'shipping':
#             title = _('Edit shipping address for «%s»')
#             form = address_forms.ShippingAddressForm
#         else:
#             title = _('Edit address for «%s»')
#             form = address_forms.AddressForm
#
#     return generic.edit_related_to_entity(request, address_id, Address, form, title_format=title)


# @login_required
# @permission_required('persons')
# def add(request, entity_id):
#     warnings.warn('persons.views.address.add() is deprecated.', DeprecationWarning)
#     return abstract_add_address(request, entity_id)


# @login_required
# @permission_required('persons')
# def add_billing(request, entity_id):
#     warnings.warn('persons.views.address.add_billing() is deprecated.', DeprecationWarning)
#     return abstract_add_billing_address(request, entity_id)


# @login_required
# @permission_required('persons')
# def add_shipping(request, entity_id):
#     warnings.warn('persons.views.address.add_shipping() is deprecated.', DeprecationWarning)
#     return abstract_add_shipping_address(request, entity_id)


# @login_required
# @permission_required('persons')
# def edit(request, address_id):
#     warnings.warn('persons.views.address.edit() is deprecated.', DeprecationWarning)
#     return abstract_edit_address(request, address_id)


# Class-based views  -----------------------------------------------------------

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
