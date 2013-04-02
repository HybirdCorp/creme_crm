# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from creme.creme_core.forms.csv_import import CSVImportForm4CremeEntity, extractorfield_factory

from ..models import Address


_FIELD_NAMES = list(Address._INFO_FIELD_NAMES) #TODO: use introspection to get editable fields ??

try:
    _FIELD_NAMES.remove('name')
except ValueError:
    pass

#TODO: factorise (MergeForm) ?
_BILL_PREFIX = 'billaddr_'
_SHIP_PREFIX = 'shipaddr_'


class _PersonCSVImportForm(CSVImportForm4CremeEntity):
    class Meta:
        exclude = ('image',)

    def _save_address(self, attr_name, prefix, person, data, line):
        import_errors = self.import_errors
        address_dict = {'name': attr_name}

        for field_name in _FIELD_NAMES:
            address_dict[field_name] = data[prefix + field_name].extract_value(line, import_errors)

        if any(address_dict.itervalues()):
            address_dict['owner'] = person
            setattr(person, attr_name, Address.objects.create(**address_dict))
            return True

        return False

    def _post_instance_creation(self, instance, line):
        super(_PersonCSVImportForm, self)._post_instance_creation(instance, line)
        data    = self.cleaned_data
        save_address    = self._save_address
        change4billing  = save_address('billing_address',  _BILL_PREFIX, instance, data, line)
        change4shipping = save_address('shipping_address', _SHIP_PREFIX, instance, data, line)

        if change4billing or change4shipping:
            instance.save()


def get_csv_form_builder(header_dict, choices):
    get_field_by_name = Address._meta.get_field_by_name
    attrs = {}
    billing_address_fnames = []
    shipping_address_fnames = []

    for field_name in _FIELD_NAMES:
        field = get_field_by_name(field_name)[0]

        form_fieldname = _BILL_PREFIX + field_name
        attrs[form_fieldname] = extractorfield_factory(field, header_dict, choices)
        billing_address_fnames.append(form_fieldname)

        form_fieldname = _SHIP_PREFIX + field_name
        attrs[form_fieldname] = extractorfield_factory(field, header_dict, choices)
        shipping_address_fnames.append(form_fieldname)

    attrs['blocks'] = CSVImportForm4CremeEntity.blocks.new(
                            ('billing_address',  _(u'Billing address'),  billing_address_fnames),
                            ('shipping_address', _(u'Shipping address'), shipping_address_fnames)
                        )

    return type('PersonCSVImportForm', (_PersonCSVImportForm,), attrs)
