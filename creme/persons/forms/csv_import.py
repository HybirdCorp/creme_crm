# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from creme_core.forms.csv_import import CSVImportForm4CremeEntity, extractorfield_factory
from django.utils.translation import ugettext as _

from persons.models import Address


def get_csv_form_builder(header_dict, choices):
    get_field_by_name = Address._meta.get_field_by_name

    f_address = get_field_by_name('address')[0]
    f_po_box  = get_field_by_name('po_box')[0]
    f_city    = get_field_by_name('city')[0]
    f_state   = get_field_by_name('state')[0]
    f_zipcode = get_field_by_name('zipcode')[0]
    f_country = get_field_by_name('country')[0]
    f_dpt     = get_field_by_name('department')[0]


    class PersonCSVImportForm(CSVImportForm4CremeEntity):
        billing_address    = extractorfield_factory(f_address, header_dict, choices)
        billing_po_box     = extractorfield_factory(f_po_box,  header_dict, choices)
        billing_city       = extractorfield_factory(f_city,    header_dict, choices)
        billing_state      = extractorfield_factory(f_state,   header_dict, choices)
        billing_zipcode    = extractorfield_factory(f_zipcode, header_dict, choices)
        billing_country    = extractorfield_factory(f_country, header_dict, choices)
        billing_department = extractorfield_factory(f_dpt,     header_dict, choices)

        shipping_address    = extractorfield_factory(f_address, header_dict, choices)
        shipping_po_box     = extractorfield_factory(f_po_box,  header_dict, choices)
        shipping_city       = extractorfield_factory(f_city,    header_dict, choices)
        shipping_state      = extractorfield_factory(f_state,   header_dict, choices)
        shipping_zipcode    = extractorfield_factory(f_zipcode, header_dict, choices)
        shipping_country    = extractorfield_factory(f_country, header_dict, choices)
        shipping_department = extractorfield_factory(f_dpt,     header_dict, choices)

        class Meta(CSVImportForm4CremeEntity.Meta):
            exclude = CSVImportForm4CremeEntity.Meta.exclude + ('billing_address', 'shipping_address')

        blocks = CSVImportForm4CremeEntity.blocks.new(
                        ('billing_address', _(u'Billing address'), ['billing_address', 'billing_po_box', 'billing_city',
                                                                    'billing_state', 'billing_zipcode', 'billing_country', 'billing_department'
                                                                   ]
                        ),
                        ('shipping_address', _(u'Shipping address'), ['shipping_address', 'shipping_po_box', 'shipping_city',
                                                                      'shipping_state', 'shipping_zipcode', 'shipping_country', 'shipping_department'
                                                                     ]
                        )
                    )

        def _save_address(self, attr_name, prefix, contact, cleaned_data, line):
            address_dict = {
                            'name':       attr_name,
                            'address':    cleaned_data[prefix + 'address'].extract_value(line),
                            'po_box':     cleaned_data[prefix + 'po_box'].extract_value(line),
                            'city':       cleaned_data[prefix + 'city'].extract_value(line),
                            'state':      cleaned_data[prefix + 'state'].extract_value(line),
                            'zipcode':    cleaned_data[prefix + 'zipcode'].extract_value(line),
                            'country':    cleaned_data[prefix + 'country'].extract_value(line),
                            'department': cleaned_data[prefix + 'department'].extract_value(line),
                           }

            if any(address_dict.itervalues()): #TODO: copy this way for regular addresses :)
                address_dict['owner'] = contact
                setattr(contact, attr_name, Address.objects.create(**address_dict))
                return True

            return False

        def _post_instance_creation(self, instance, line):
            super(PersonCSVImportForm, self)._post_instance_creation(instance, line)
            cleaned_data    = self.cleaned_data
            change4billing  = self._save_address('billing_address',  'billing_',  instance, cleaned_data, line)
            change4shipping = self._save_address('shipping_address', 'shipping_', instance, cleaned_data, line)

            if change4billing or change4shipping:
                instance.save()


    return PersonCSVImportForm
