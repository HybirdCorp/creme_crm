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

from itertools import chain

from django.utils.translation import ugettext as _

from creme_core.forms.merge import MergeEntitiesBaseForm, mergefield_factory

from persons.models import Contact, Address


_FIELD_NAMES = Address._INFO_FIELD_NAMES

#TODO: factorise with csv_import.py ?
#TODO: code can be simplified (see BaseForm ??)
def get_merge_form_builder():
    get_field_by_name = Address._meta.get_field_by_name

    f_name    =  get_field_by_name('name')[0]
    f_address = get_field_by_name('address')[0]
    f_po_box  = get_field_by_name('po_box')[0]
    f_city    = get_field_by_name('city')[0]
    f_state   = get_field_by_name('state')[0]
    f_zipcode = get_field_by_name('zipcode')[0]
    f_country = get_field_by_name('country')[0]
    f_dpt     = get_field_by_name('department')[0]


    class PersonMergeImportForm(MergeEntitiesBaseForm):
        billaddr_name       = mergefield_factory(f_name)
        billaddr_address    = mergefield_factory(f_address)
        billaddr_po_box     = mergefield_factory(f_po_box)
        billaddr_city       = mergefield_factory(f_city)
        billaddr_state      = mergefield_factory(f_state)
        billaddr_zipcode    = mergefield_factory(f_zipcode)
        billaddr_country    = mergefield_factory(f_country)
        billaddr_department = mergefield_factory(f_dpt)

        shipaddr_name       = mergefield_factory(f_name)
        shipaddr_address    = mergefield_factory(f_address)
        shipaddr_po_box     = mergefield_factory(f_po_box)
        shipaddr_city       = mergefield_factory(f_city)
        shipaddr_state      = mergefield_factory(f_state)
        shipaddr_zipcode    = mergefield_factory(f_zipcode)
        shipaddr_country    = mergefield_factory(f_country)
        shipaddr_department = mergefield_factory(f_dpt)

        #class Meta:
            #exclude = ('language',) #TODO

        blocks = MergeEntitiesBaseForm.blocks.new(
                    ('billing_address',  _(u'Billing address'),  ['billaddr_' + fn for fn in _FIELD_NAMES]),
                    ('shipping_address', _(u'Shipping address'), ['shipaddr_' + fn for fn in _FIELD_NAMES]),
                  )

        def __init__(self, entity1, entity2, *args, **kwargs):
            if getattr(entity1, 'is_user', None) or getattr(entity2, 'is_user', None):#TODO: create a ContactMergeForm ?
                raise self.CanNotMergeError(_('Can not merge a Contact that represents a user.'))

            super(PersonMergeImportForm, self).__init__(entity1, entity2, *args, **kwargs)

        def _build_initial_address_dict(self, address, initial, prefix):
            getter = (lambda fname: '') if address is None else \
                     lambda fname: getattr(address, fname)

            for fname in _FIELD_NAMES:
                initial[prefix + fname] = getter(fname)

        def _build_initial_dict(self, entity):
            initial = super(PersonMergeImportForm, self)._build_initial_dict(entity)

            build = self._build_initial_address_dict
            build(entity.billing_address,  initial, 'billaddr_')
            build(entity.shipping_address, initial, 'shipaddr_')

            return initial

        def _save_address(self, entity1, entity2, attr_name, cleaned_data, prefix):
            address = getattr(entity1, attr_name)
            was_none = False

            if address is None:
                address = getattr(entity2, attr_name) or Address()
                address.owner = entity1
                was_none = True

            for fname in _FIELD_NAMES:
                setattr(address, fname, cleaned_data[prefix + fname])

            if address:
                address.save()
                setattr(entity1, attr_name, address)
                return was_none, ()

            if not was_none:
                setattr(entity1, attr_name, None)
                return True, [address] if address.pk else ()

            return True, ()

        def _post_entity1_update(self, entity1, entity2, cleaned_data):
            save_address = self._save_address

            must_save1, to_del1 = save_address(entity1, entity2, 'billing_address',  cleaned_data, 'billaddr_')
            must_save2, to_del2 = save_address(entity1, entity2, 'shipping_address', cleaned_data, 'shipaddr_')

            if must_save1 or must_save2:
                entity1.save()

            for address in chain(to_del1, to_del2):
                address.delete()


    return PersonMergeImportForm
