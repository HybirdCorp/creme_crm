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

"""Generate a vCard from Contact object"""

from creme.persons import get_address_model
#from creme.persons.models import Address

from .vcf_lib import vCard
from .vcf_lib.vcard import Address as VcfAddress, Name as VcfName


Address = get_address_model()


class VcfGenerator(object):
    def __init__(self, contact):
#        self.first_name = contact.first_name    or ''
#        self.last_name = contact.last_name
#        self.civility = contact.civility
#        self.phone = contact.phone
#        self.mobile = contact.mobile            or ''
#        self.fax = contact.fax                  or ''
#        self.email = contact.email              or ''
#        self.url = contact.url_site             or ''
        self.first_name = getattr(contact, 'first_name', None) or ''
        self.last_name  = getattr(contact, 'last_name', None) or ''
        self.civility   = getattr(contact, 'civility', None)
        self.phone      = getattr(contact, 'phone', None) #TODO: or ''  ??
        self.mobile     = getattr(contact, 'mobile', None) or ''
        self.fax        = getattr(contact, 'fax', None) or ''
        self.email      = getattr(contact, 'email', None) or ''
        self.url        = getattr(contact, 'url_site', None) or ''

        # TODO Manage several employers
        #employer = contact.get_employers()[:1]
        #self.employer = employer[0] if employer else None
        self.employer = contact.get_employers().first()

        self.address_field_names = Address.info_field_names()
        self.addresses = Address.objects.filter(object_id=contact.id).order_by('id')

#    _INFO_FIELD_NAMES = ('name', 'address', 'po_box', 'zipcode', 'city', 'department', 'state', 'country')

#    @staticmethod
#    def address_equality(address1, address2):  # TODO : overload __eq__() in Address?
    def address_equality(self, address1, address2):  # TODO : overload __eq__() in Address?
        if address1 is not None and address2 is not None:
            return all(getattr(address1, fname) == getattr(address2, fname)
##                        for fname in VcfGenerator._INFO_FIELD_NAMES
#                        for fname in Address.info_field_names()
                        for fname in self.address_field_names
                      )

        return False

    @staticmethod
    def generate_address(address):
        return VcfAddress(address.address,
                          address.city,
                          address.department,
                          address.zipcode,
                          address.country,
                          address.po_box,
                         )

    @staticmethod
    def generate_name(last, first, civility=''):
        return VcfName(last, first, '', civility, '')

    def serialize(self):
        vc = vCard()

        vc.add('n')
        if self.civility:
            vc.n.value = VcfGenerator.generate_name(self.last_name, self.first_name, self.civility.title)
        else:
            vc.n.value = VcfGenerator.generate_name(self.last_name, self.first_name)

        vc.add('fn')
        vc.fn.value = self.first_name + ' ' + self.last_name

#        addr_equal = VcfGenerator.address_equality
        addr_equal = self.address_equality
        addresses = []
        addresses.extend(addr
                            for addr in self.addresses
                                if not any(addr_equal(addr, other) for other in addresses)
                        )

        for address in addresses:
            vc.add('adr').value = VcfGenerator.generate_address(address)

        if self.employer:
            vc.add('org')
            vc.org.value = [self.employer.name]

        if self.phone:
            vc.add('phone').value = self.phone
            vc.phone.name = 'TEL'
            vc.phone.type_param = 'WORK'

        if self.mobile:
            vc.add('cell').value = self.mobile
            vc.cell.name = 'TEL'
            vc.cell.type_param = 'CELL'

        if self.fax:
            vc.add('fax').value = self.fax
            vc.fax.name = 'TEL'
            vc.fax.type_param = 'FAX'

        if self.email:
            vc.add('email').value = self.email
            vc.email.type_param = 'INTERNET'

        if self.url:
            vc.add('url').value = self.url

        return vc.serialize()
