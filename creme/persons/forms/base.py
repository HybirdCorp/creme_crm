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

import logging

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.forms import CremeEntityForm
from creme.creme_core.models import CremeEntity

from .address import AddressForm


logger = logging.getLogger(__name__)

_BILLING_ADDRESS_FIELD  = 'billing_address'
_SHIPPING_ADDRESS_FIELD = 'shipping_address'


def _get_address_field_names(addr_fieldname):
    form = AddressForm(entity=None, user=None, prefix=addr_fieldname)
    return [form.add_prefix(name) for name in form.base_fields.iterkeys()]


class _BasePersonForm(CremeEntityForm):
    blocks = CremeEntityForm.blocks.new(
                ('billing_address',  _(u'Billing address'),  _get_address_field_names(_BILLING_ADDRESS_FIELD)),
                ('shipping_address', _(u'Shipping address'), _get_address_field_names(_SHIPPING_ADDRESS_FIELD)),
             )

    class Meta(CremeEntityForm.Meta):
        model = CremeEntity # Overload me

    # Used by template (address blocks have a special layout + buttons to copy addresses)
    # See _init_address_fields()
    hide_billing_address  = False
    hide_shipping_address = False

    def __init__(self, *args, **kwargs):
        super(_BasePersonForm, self).__init__(*args, **kwargs)

        fconfig = self.fields_configs.get_4_model(self.instance.__class__)
        self._init_address_fields(fconfig, _BILLING_ADDRESS_FIELD)
        self._init_address_fields(fconfig, _SHIPPING_ADDRESS_FIELD)

    def _init_address_fields(self, fconfig, addr_fieldname):
        if fconfig.is_fieldname_hidden(addr_fieldname):
            setattr(self, 'hide_' + addr_fieldname, True)
            return

        fields = self.fields
        instance = self.instance
        address_form = AddressForm(entity=instance, user=self.user, prefix=addr_fieldname,
                                   instance=getattr(instance, addr_fieldname),
                                  ) #TODO factorise ??
        initial = {}

#        for name, field in address_form.base_fields.iteritems():
        for name, field in address_form.fields.iteritems():
            final_name = address_form.add_prefix(name)
            fields[final_name]  = field
            initial[final_name] = address_form.initial.get(name)

        self.initial.update(initial)

    def _save_address(self, addr_fieldname):
        instance = self.instance
        save_instance = False
        address = getattr(instance, addr_fieldname)
        addr_form = AddressForm(entity=instance, user=self.user, instance=address,
                                prefix=addr_fieldname, data=self.data,
                               )

        if addr_form.is_valid():
            if address is not None:
                addr_form.save()
            elif addr_form.instance: # Do not save empty address
                setattr(instance, addr_fieldname, addr_form.save())
                save_instance = True
        else:
            logger.debug('Address form (%s) is not valid: %s', addr_fieldname, addr_form.errors)

        return save_instance

    def save(self, *args, **kwargs):
        instance = super(_BasePersonForm, self).save(*args, **kwargs)
        change4billing  = self._save_address(_BILLING_ADDRESS_FIELD)
        change4shipping = self._save_address(_SHIPPING_ADDRESS_FIELD)

        if change4billing or change4shipping:
            instance.save() # Saved twice because of bidirectionnal pk (TODO: change ??)

        return instance
