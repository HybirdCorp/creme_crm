# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from creme_core.forms.csv_import import CSVImportForm4CremeEntity, extractorfield_factory

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
        billaddr_address    = extractorfield_factory(f_address, header_dict, choices)
        billaddr_po_box     = extractorfield_factory(f_po_box,  header_dict, choices)
        billaddr_city       = extractorfield_factory(f_city,    header_dict, choices)
        billaddr_state      = extractorfield_factory(f_state,   header_dict, choices)
        billaddr_zipcode    = extractorfield_factory(f_zipcode, header_dict, choices)
        billaddr_country    = extractorfield_factory(f_country, header_dict, choices)
        billaddr_department = extractorfield_factory(f_dpt,     header_dict, choices)

        shipaddr_address    = extractorfield_factory(f_address, header_dict, choices)
        shipaddr_po_box     = extractorfield_factory(f_po_box,  header_dict, choices)
        shipaddr_city       = extractorfield_factory(f_city,    header_dict, choices)
        shipaddr_state      = extractorfield_factory(f_state,   header_dict, choices)
        shipaddr_zipcode    = extractorfield_factory(f_zipcode, header_dict, choices)
        shipaddr_country    = extractorfield_factory(f_country, header_dict, choices)
        shipaddr_department = extractorfield_factory(f_dpt,     header_dict, choices)

        class Meta:
            #exclude = ('language',)
            exclude = ('image',)

        blocks = CSVImportForm4CremeEntity.blocks.new(
                        ('billing_address', _(u'Billing address'), ['billaddr_address', 'billaddr_po_box', 'billaddr_city',
                                                                    'billaddr_state', 'billaddr_zipcode', 'billaddr_country', 'billaddr_department'
                                                                   ]
                        ),
                        ('shipping_address', _(u'Shipping address'), ['shipaddr_address', 'shipaddr_po_box', 'shipaddr_city',
                                                                      'shipaddr_state', 'shipaddr_zipcode', 'shipaddr_country', 'shipaddr_department'
                                                                     ]
                        )
                    )

        def _save_address(self, attr_name, prefix, contact, cleaned_data, line):
            import_errors = self.import_errors
            address_dict = {'name':       attr_name,
                            'address':    cleaned_data[prefix + 'address'].extract_value(line, import_errors),
                            'po_box':     cleaned_data[prefix + 'po_box'].extract_value(line, import_errors),
                            'city':       cleaned_data[prefix + 'city'].extract_value(line, import_errors),
                            'state':      cleaned_data[prefix + 'state'].extract_value(line, import_errors),
                            'zipcode':    cleaned_data[prefix + 'zipcode'].extract_value(line, import_errors),
                            'country':    cleaned_data[prefix + 'country'].extract_value(line, import_errors),
                            'department': cleaned_data[prefix + 'department'].extract_value(line, import_errors),
                           }

            if any(address_dict.itervalues()):
                address_dict['owner'] = contact
                setattr(contact, attr_name, Address.objects.create(**address_dict))
                return True

            return False

        def _post_instance_creation(self, instance, line):
            super(PersonCSVImportForm, self)._post_instance_creation(instance, line)
            cleaned_data    = self.cleaned_data
            save_address    = self._save_address
            change4billing  = save_address('billing_address',  'billaddr_', instance, cleaned_data, line)
            change4shipping = save_address('shipping_address', 'shipaddr_', instance, cleaned_data, line)

            if change4billing or change4shipping:
                instance.save()


    return PersonCSVImportForm
