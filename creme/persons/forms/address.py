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

import logging
import warnings

from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.forms import CremeModelForm
from creme.creme_core.gui.custom_form import ExtraFieldGroup
from creme.creme_core.models import FieldsConfig

from .. import get_address_model

logger = logging.getLogger(__name__)
Address = get_address_model()


class AddressForm(CremeModelForm):
    class Meta(CremeModelForm.Meta):
        model = Address

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._entity = entity

    def save(self, *args, **kwargs):
        self.instance.owner = self._entity
        return super().save(*args, **kwargs)


class UnnamedAddressForm(AddressForm):
    class Meta(AddressForm.Meta):
        exclude = ('name',)


# Does not inherit CremeModelForm, so there is no use of FieldsConfig
#   - all fields are used
#   - no SQL query
class _AuxiliaryAddressForm(ModelForm):
    class Meta(AddressForm.Meta):
        model = Address
        exclude = ('name',)

    def __init__(self, *args, **kwargs):
        warnings.warn('_AuxiliaryAddressForm is deprecated', DeprecationWarning)
        super().__init__(*args, **kwargs)


class _FieldAddressForm(UnnamedAddressForm):
    field_name = 'OVERRIDE ME'
    verbose_name = 'OVERRIDE ME'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO: should be in the view ?
        field_name = self.field_name
        if FieldsConfig.objects.get_for_model(
            self._entity.__class__
        ).is_fieldname_hidden(field_name):
            raise ConflictError(f'"{field_name}" is hidden & so it cannot be edited')

    def save(self, *args, **kwargs):
        address = self.instance
        address.name = str(self.verbose_name)

        entity = self._entity
        super().save(*args, **kwargs)

        setattr(entity, self.field_name, address)
        entity.save()  # TODO: save only one field ?

        return address


class BillingAddressForm(_FieldAddressForm):
    field_name = 'billing_address'
    verbose_name = _('Billing address')


class ShippingAddressForm(_FieldAddressForm):
    field_name = 'shipping_address'
    verbose_name = _('Shipping address')


class AddressesGroup(ExtraFieldGroup):
    template_name = 'persons/forms/addresses-block.html'
    extra_group_id = 'persons-addresses'
    name = _('Addresses')

    sub_form_class = UnnamedAddressForm

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.address_fks = [
            field
            for field in self.model._meta.fields
            if field.is_relation and field.remote_field.model == Address
        ]

    def _address_formfield(self, instance, user, addr_fieldname):
        address_form = self.sub_form_class(
            entity=instance,
            user=user,
            prefix=addr_fieldname,
            instance=getattr(instance, addr_fieldname),
        )

        for name, field in address_form.fields.items():
            field.initial = address_form.initial.get(name)

            yield address_form.add_prefix(name), field

    def _visible_address_fks(self):
        is_field_hidden = FieldsConfig.objects.get_for_model(self.model).is_field_hidden

        for fk in self.address_fks:
            if not is_field_hidden(fk):
                yield fk

    def formfields(self, instance, user):
        for fk in self._visible_address_fks():
            yield from self._address_formfield(
                instance=instance, user=user, addr_fieldname=fk.name,
            )

    def get_context(self):
        ctxt = super().get_context()
        ctxt['address_fields'] = [*self._visible_address_fks()]

        return ctxt

    def _save_address(self, form, addr_fieldname, verbose_name):
        instance = form.instance
        save_instance = False
        address = getattr(instance, addr_fieldname)
        addr_form = self.sub_form_class(
            entity=instance,
            user=form.user,
            instance=address,
            prefix=addr_fieldname,
            data=form.data,
        )

        if addr_form.is_valid():
            if address is not None:
                addr_form.save()
            elif addr_form.instance:  # Do not save empty address
                addr_form.instance.name = str(verbose_name)
                setattr(instance, addr_fieldname, addr_form.save())
                save_instance = True
        else:
            logger.debug(
                'Address form (%s) is not valid: %s',
                addr_fieldname, addr_form.errors,
            )

        return save_instance

    def save(self, form):
        save_addr = self._save_address

        changed = False
        for fk in self._visible_address_fks():
            changed |= save_addr(form, fk.name, fk.verbose_name)

        # Saved twice because of bidirectional pk
        return changed
