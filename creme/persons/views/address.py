# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2017  Hybird
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

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views import generic

from .. import get_address_model
from ..forms import address as address_forms


Address = get_address_model()


def abstract_add_address(request, entity_id, form=address_forms.AddressForm,
                         title=_(u'Adding address to «%s»'),
                         submit_label=_(u'Save the address'),
                        ):
    return generic.add_to_entity(request, entity_id, form, title=title, submit_label=submit_label)


def abstract_add_billing_address(request, entity_id, form=address_forms.BillingAddressForm,
                                 title=_(u'Adding billing address to «%s»'),
                                 submit_label=_(u'Save the address')
                                ):
    return generic.add_to_entity(request, entity_id, form, title=title, submit_label=submit_label)


def abstract_add_shipping_address(request, entity_id, form=address_forms.ShippingAddressForm,
                                  title=_(u'Adding shipping address to «%s»'),
                                  submit_label=_(u'Save the address'),
                                ):
    return generic.add_to_entity(request, entity_id, form, title=title, submit_label=submit_label)


def abstract_edit_address(request, address_id,
                          # form=address_forms.AddressForm,
                          form=None,
                          # title=_(u'Address for «%s»'),
                          title=None,
                         ):
    if form is None or title is None:
        address_type = request.GET.get('type')

        if address_type == 'billing':
            title = _(u'Edit billing address for «%s»')
            form = address_forms.BillingAddressForm
        elif address_type == 'shipping':
            title = _(u'Edit shipping address for «%s»')
            form = address_forms.ShippingAddressForm
        else:
            title = _(u'Edit address for «%s»')
            form = address_forms.AddressForm

    return generic.edit_related_to_entity(request, address_id, Address, form, title_format=title)


@login_required
@permission_required('persons')
def add(request, entity_id):
    return abstract_add_address(request, entity_id)


@login_required
@permission_required('persons')
def add_billing(request, entity_id):
    return abstract_add_billing_address(request, entity_id)


@login_required
@permission_required('persons')
def add_shipping(request, entity_id):
    return abstract_add_shipping_address(request, entity_id)


@login_required
@permission_required('persons')
def edit(request, address_id):
    return abstract_edit_address(request, address_id)
