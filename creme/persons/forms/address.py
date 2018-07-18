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

from django.forms import ModelForm
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.forms import CremeModelForm
from creme.creme_core.models import FieldsConfig

from .. import get_address_model


class AddressForm(CremeModelForm):
    class Meta(CremeModelForm.Meta):
        model = get_address_model()

    def __init__(self, entity, *args, **kwargs):
        # super(AddressForm, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)
        self._entity = entity

    def save(self, *args, **kwargs):
        self.instance.owner = self._entity
        # return super(AddressForm, self).save(*args, **kwargs)
        return super().save(*args, **kwargs)


class UnnamedAddressForm(AddressForm):
    class Meta(AddressForm.Meta):
        exclude = ('name',)


# Does not inherit CremeModelForm, so there is no use of FieldsConfig
#   - all fields are used
#   - no SQL query
class _AuxiliaryAddressForm(ModelForm):
    class Meta(AddressForm.Meta):
        model = get_address_model()
        exclude = ('name',)


class _FieldAddressForm(UnnamedAddressForm):
    field_name = 'OVERLOAD'
    verbose_name = 'OVERLOAD'

    def __init__(self, *args, **kwargs):
        # super(_FieldAddressForm, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)

        # TODO: should be in the view ?
        field_name = self.field_name
        if FieldsConfig.get_4_model(self._entity.__class__).is_fieldname_hidden(field_name):
            raise ConflictError('"{}" is hidden & so it cannot be edited'.format(field_name))

    def save(self, *args, **kwargs):
        address = self.instance
        address.name = str(self.verbose_name)

        entity = self._entity
        # super(_FieldAddressForm, self).save(*args, **kwargs)
        super().save(*args, **kwargs)

        setattr(entity, self.field_name, address)
        entity.save()  # TODO: with django 1.5: save only one field

        return address


class BillingAddressForm(_FieldAddressForm):
    field_name = 'billing_address'
    verbose_name = _(u'Billing address')


class ShippingAddressForm(_FieldAddressForm):
    field_name = 'shipping_address'
    verbose_name = _(u'Shipping address')
