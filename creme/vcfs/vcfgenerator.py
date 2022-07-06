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

from creme.creme_core.models import FieldsConfig
from creme.persons import get_address_model

from .vcf_lib import vCard
from .vcf_lib.vcard import Address as VcfAddress
from .vcf_lib.vcard import Name as VcfName

Address = get_address_model()


class VcfGenerator:
    """Generate a vCard from Contact object"""
    def __init__(self, contact):
        is_hidden = FieldsConfig.objects.get_for_model(contact.__class__).is_fieldname_hidden

        def get_field_value(fname, default=None):
            return default if is_hidden(fname) else getattr(contact, fname, default)

        self.first_name = get_field_value('first_name', None) or ''
        self.last_name  = get_field_value('last_name', '')
        self.civility   = get_field_value('civility')
        self.phone      = get_field_value('phone')
        self.mobile     = get_field_value('mobile')
        self.fax        = get_field_value('fax')
        self.email      = get_field_value('email')
        self.url        = get_field_value('url_site')

        # TODO: manage several employers
        self.employer = contact.get_employers().first()

        self._address_field_names = {*Address.info_field_names()}
        self.addresses = Address.objects.filter(object_id=contact.id).order_by('id')

    def address_equality(self, address1, address2):  # TODO : overload __eq__() in Address?
        if address1 is not None and address2 is not None:
            return all(
                getattr(address1, fname) == getattr(address2, fname)
                for fname in self._address_field_names
            )

        return False

    def generate_address(self, address):
        fnames = self._address_field_names
        get_field_value = (
            lambda fname: '' if fname not in fnames else
                          getattr(address, fname) or ''
        )

        return VcfAddress(
            street=get_field_value('address'),
            city=get_field_value('city'),
            region=get_field_value('department'),
            code=get_field_value('zipcode'),
            country=get_field_value('country'),
            box=get_field_value('po_box'),
        )

    def serialize(self):
        vc = vCard()

        last_name = self.last_name
        first_name = self.first_name

        vc.add('n')
        civility = self.civility
        vc.n.value = VcfName(
            family=last_name,
            given=first_name,
            prefix=civility.title if civility else '',
        )

        vc.add('fn')
        vc.fn.value = first_name + ' ' + last_name

        addr_equal = self.address_equality
        addresses = []
        addresses.extend(
            addr
            for addr in self.addresses
            if not any(addr_equal(addr, other) for other in addresses)
        )

        generate_address = self.generate_address
        for address in addresses:
            vc.add('adr').value = generate_address(address)

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
