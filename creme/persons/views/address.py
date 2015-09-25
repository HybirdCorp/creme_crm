# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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
from creme.creme_core.views.generic import add_to_entity, edit_related_to_entity

from .. import get_address_model
from ..forms.address import AddressForm, BillingAddressForm, ShippingAddressForm
#from ..models import Address


@login_required
@permission_required('persons')
def add(request, entity_id):
    return add_to_entity(request, entity_id, AddressForm,
                         _(u'Adding address to «%s»'),
                         submit_label=_('Save the address'),
                        )

@login_required
@permission_required('persons')
def add_billing(request, entity_id):
    return add_to_entity(request, entity_id, BillingAddressForm,
                         _(u'Adding billing address to «%s»'),
                         submit_label=_('Save the address'),
                        )

@login_required
@permission_required('persons')
def add_shipping(request, entity_id):
    return add_to_entity(request, entity_id, ShippingAddressForm,
                         _(u'Adding shipping address to «%s»'),
                         submit_label=_('Save the address'),
                        )

@login_required
@permission_required('persons')
def edit(request, address_id):
#    return edit_related_to_entity(request, address_id, Address, AddressForm,
    return edit_related_to_entity(request, address_id, get_address_model(), AddressForm,
                                  _(u'Address for «%s»'),
                                 )
