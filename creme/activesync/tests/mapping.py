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

from datetime import date
from os.path import join, dirname, abspath
from xml.etree.ElementTree import XML, tostring

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from django.test import TestCase
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.files import File

from creme_core.models import Relation, RelationType
from creme_core.tests.base import CremeTestCase

from persons.models import Address, Contact, Organisation, Civility
from persons.constants import REL_SUB_EMPLOYED_BY

from activesync.mappings.utils import serialize_entity
from activesync.mappings.contact import CREME_CONTACT_MAPPING


DEFAULT_CHUNK_SIZE = File.DEFAULT_CHUNK_SIZE

class MappingTestCase(CremeTestCase):
    def setUp(self):
        self.xml_path = join(dirname(abspath(__file__)), 'data', 'mappings')
        self.populate('creme_core', 'persons', )

    def _open_n_read(self, filename, mode='r'):
        path = join(self.xml_path, filename)
        content = StringIO()

        with open(path, mode) as f:
            for ch in f.read(DEFAULT_CHUNK_SIZE):
                content.write(ch)

        return_content = content.getvalue()

        content.close()

        return return_content

    def test_contact_serialization01(self):
        #TODO: Check contact image
        user = User.objects.create(username='user')

        civility = Civility.objects.create(title='Mister')
        contact = Contact.objects.create(
                            first_name="Creme",
                            last_name="Fulbert",
                            civility=civility,
                            skype="skype_number",
                            phone="+33 000000000",
                            mobile="+33 000000001",
                            email="fulbert@creme.com",
                            url_site="http://creme.com",
                            birthday=date(year=2011, month=01, day=02),
                            user=user,
                    )

        contact.billing_address = Address.objects.create(
                name='Billing Address',
                address='Hybird office',
                po_box='13000',
                city='Marseille',
                state='state',
                zipcode='zip code',
                country='France',
                department=u'Bouches-du-rhône',
                content_type_id=ContentType.objects.get_for_model(Contact).id,
                object_id=contact.id
             )
        contact.shipping_address = Address.objects.create(
                name='Shipping Address',
                address='Hybird office',
                po_box='13000',
                city='Marseille',
                state='state',
                zipcode='zip code',
                country='France',
                department=u'Bouches-du-rhône',
                content_type_id=ContentType.objects.get_for_model(Contact).id,
                object_id=contact.id
            )
        contact.save()

        organisation = Organisation.objects.create(name='Hybird', user=user)

        employed_by = RelationType.objects.get(pk=REL_SUB_EMPLOYED_BY)
        Relation.objects.create(subject_entity=contact, type=employed_by, object_entity=organisation)

        fulbert_serialized = self._open_n_read(join(self.xml_path, 'contact', 'fulbert.xml'))
#        to_parse = """<?xml version="1.0"?><Contact xmlns:A1="Contact:">%s</Contact>"""
#        xml_fulbert_serialized_str = tostring(XML(to_parse % fulbert_serialized))
#        xml_entity_serialized_str  = tostring(XML(to_parse % serialize_entity(contact, CREME_CONTACT_MAPPING)))
#        self.assertEqual(xml_fulbert_serialized_str, xml_entity_serialized_str)
        #TODO: Change this test, global string comparision is not good
        #Disabled until a real test is done
#        self.assertEqual(fulbert_serialized, serialize_entity(contact, CREME_CONTACT_MAPPING))

