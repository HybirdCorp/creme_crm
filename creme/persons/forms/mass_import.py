################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from creme.creme_core.forms.mass_import import (
    ImportForm4CremeEntity,
    extractorfield_factory,
)
from creme.creme_core.models import FieldsConfig

from .. import get_address_model

Address = get_address_model()

# TODO: factorise (MergeForm) ?
_BILL_PREFIX = 'billaddr_'
_SHIP_PREFIX = 'shipaddr_'


class _PersonMassImportForm(ImportForm4CremeEntity):
    class Meta:
        exclude = ('image',)

    # Overload by get_csv_form_builder()
    _address_field_names = ()
    _billing_address_hidden = False
    _shipping_address_hidden = False

    def _save_address(self, attr_name, prefix, person, data, line, name):
        if getattr(self, f'_{attr_name}_hidden'):
            return False

        user = self.user
        address_dict = {}
        save = False

        for field_name in self._address_field_names:
            extr_value, err_msg = data[prefix + field_name].extract_value(line, user)
            if extr_value:
                address_dict[field_name] = extr_value

            self.append_error(err_msg)

        if address_dict:
            address_dict['owner'] = person
            address_dict['name'] = name
            address = getattr(person, attr_name, None)

            try:
                if address is not None:  # Update
                    for fname, fvalue in address_dict.items():
                        setattr(address, fname, fvalue)

                    address.full_clean()
                    address.save()
                else:
                    address = Address(**address_dict)
                    address.full_clean()
                    address.save()

                    setattr(person, attr_name, address)
                    save = True
            except ValidationError as e:
                # TODO: improve append_error() ?
                for err_msg in e.messages:
                    self.append_error(err_msg)

        return save

    def _post_instance_creation(self, instance, line, updated):
        super()._post_instance_creation(instance, line, updated)
        data = self.cleaned_data
        save_address = self._save_address
        change4billing = save_address(
            'billing_address',  _BILL_PREFIX, instance, data, line, _('Billing address'),
        )
        change4shipping = save_address(
            'shipping_address', _SHIP_PREFIX, instance, data, line, _('Shipping address'),
        )

        if change4billing or change4shipping:
            instance.save()


def get_massimport_form_builder(header_dict, choices, model, base_form=_PersonMassImportForm):
    address_field_names = [*Address.info_field_names()]  # TODO: remove not-editable fields ??
    try:
        # TODO: what if name is required by configuration ?
        address_field_names.remove('name')
    except ValueError:
        pass

    attrs = {'_address_field_names': address_field_names}

    get_field = Address._meta.get_field
    fields = [get_field(field_name) for field_name in address_field_names]

    is_hidden = FieldsConfig.objects.get_for_model(model).is_fieldname_hidden

    def add_fields(attr_name, prefix):
        fnames = []
        hidden = is_hidden(attr_name)

        if not hidden:
            for field in fields:
                form_fieldname = prefix + field.name
                # attrs[form_fieldname] = form_field = extractorfield_factory(
                attrs[form_fieldname] = extractorfield_factory(
                    field, header_dict, choices,
                )

                # NB: we do not force the field to be required, in order to let
                #     user do not fill the address at all. Contacts/Organisations
                #     can be created without Address even if an Address' field is
                #     required (by using quick forms, by removing the Addresses
                #     form-block...), so it would be annoying that mass import
                #     forces the creation of the 2 Addresses.
                # if FieldsConfig.objects.get_for_model(Address).is_field_required(field):
                #     form_field.required = True

                fnames.append(form_fieldname)

        # NB: see _PersonMassImportForm._save_address()
        attrs[f'_{attr_name}_hidden'] = hidden

        return fnames

    billing_address_fnames  = add_fields('billing_address', _BILL_PREFIX)
    shipping_address_fnames = add_fields('shipping_address', _SHIP_PREFIX)

    attrs['blocks'] = ImportForm4CremeEntity.blocks.new(
        ('billing_address',  _('Billing address'),  billing_address_fnames),
        ('shipping_address', _('Shipping address'), shipping_address_fnames),
    )

    return type('PersonMassImportForm', (base_form,), attrs)
