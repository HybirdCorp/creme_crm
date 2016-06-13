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

from django.utils.translation import ugettext as _

from creme.creme_core.forms.mass_import import ImportForm4CremeEntity, extractorfield_factory
from creme.creme_core.models import FieldsConfig

from .. import get_address_model


Address = get_address_model()

# TODO: factorise (MergeForm) ?
_BILL_PREFIX = 'billaddr_'
_SHIP_PREFIX = 'shipaddr_'


class _PersonCSVImportForm(ImportForm4CremeEntity):
    class Meta:
        exclude = ('image',)

    # Overload by get_csv_form_builder()
    _address_field_names = ()
    _billing_address_hidden = False
    _shipping_address_hidden = False

    def _save_address(self, attr_name, prefix, person, data, line, name):
        if getattr(self, '_%s_hidden' % attr_name):
            return False

        address_dict = {}
        save = False

        for field_name in self._address_field_names:
            extr_value, err_msg = data[prefix + field_name].extract_value(line)
            if extr_value:
                address_dict[field_name] = extr_value

            self.append_error(line, err_msg, person)

        if address_dict:
            address_dict['owner'] = person
            address_dict['name'] = name
            address = getattr(person, attr_name, None)

            if address is not None:  # Update
                for fname, fvalue in address_dict.iteritems():
                    setattr(address, fname, fvalue)

                address.save()
            else:
                setattr(person, attr_name, Address.objects.create(**address_dict))
                save = True

        return save

    def _post_instance_creation(self, instance, line, updated):
        super(_PersonCSVImportForm, self)._post_instance_creation(instance, line, updated)
        data = self.cleaned_data
        save_address    = self._save_address
        change4billing  = save_address('billing_address',  _BILL_PREFIX, instance, data, line, _('Billing address'))
        change4shipping = save_address('shipping_address', _SHIP_PREFIX, instance, data, line, _('Shipping address'))

        if change4billing or change4shipping:
            instance.save()


def get_csv_form_builder(header_dict, choices, model):
    address_field_names = list(Address.info_field_names())  # TODO: remove not-editable fields ??
    try:
       address_field_names.remove('name')
    except ValueError:
       pass

    attrs = {'_address_field_names': address_field_names}

    get_field = Address._meta.get_field
    fields = [get_field(field_name) for field_name in address_field_names]

    is_hidden = FieldsConfig.get_4_model(model).is_fieldname_hidden

    def add_fields(attr_name, prefix):
        fnames = []
        hidden = is_hidden(attr_name)

        if not hidden:
            for field in fields:
                form_fieldname = prefix + field.name
                attrs[form_fieldname] = extractorfield_factory(field, header_dict, choices)
                fnames.append(form_fieldname)

        attrs['_%s_hidden' % attr_name] = hidden

        return fnames

    billing_address_fnames  = add_fields('billing_address', _BILL_PREFIX)
    shipping_address_fnames = add_fields('shipping_address', _SHIP_PREFIX)

    attrs['blocks'] = ImportForm4CremeEntity.blocks.new(
                            ('billing_address',  _(u'Billing address'),  billing_address_fnames),
                            ('shipping_address', _(u'Shipping address'), shipping_address_fnames)
                        )

    return type('PersonCSVImportForm', (_PersonCSVImportForm,), attrs)
