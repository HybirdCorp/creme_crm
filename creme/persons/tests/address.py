# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType

    from creme_core.tests.base import CremeTestCase

    from persons.models import Address, Organisation
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('AddressTestCase',)


class AddressTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_config')

    def setUp(self):
        self.login()

        self.orga = Organisation.objects.create(user=self.user, name='Nerv')

    def _create_address(self, orga, name, address, po_box, city, state, zipcode, country, department):
        response = self.client.post('/persons/address/add/%s' % orga.id,
                                    data={'name':       name,
                                          'address':    address,
                                          'po_box':     po_box,
                                          'city':       city,
                                          'state':      state,
                                          'zipcode':    zipcode,
                                          'country':    country,
                                          'department': department,
                                         }
                                   )
        self.assertEqual(response.status_code, 200)
        self.assertNoFormError(response)

    def test_createview(self):
        orga = self.orga

        self.assertEqual(0, Address.objects.filter(object_id=orga.id).count())

        response = self.client.get('/persons/address/add/%s' % orga.id)
        self.assertEqual(200, response.status_code)

        name = 'Address#1'
        address_value = '21 jump street'
        po_box = 'Popop'
        city = 'Antlantis'
        state = '??'
        zipcode = '424242'
        country = 'wtf'
        department = 'rucrazy'

        self._create_address(orga, name, address_value, po_box, city, state, zipcode, country, department)

        addresses = Address.objects.filter(object_id=orga.id)
        self.assertEqual(1, len(addresses))

        address = addresses[0]
        self.assertEqual(name,       address.name)
        self.assertEqual(address_value, address.address)
        self.assertEqual(po_box,     address.po_box)
        self.assertEqual(city,       address.city)
        self.assertEqual(state,      address.state)
        self.assertEqual(zipcode,    address.zipcode)
        self.assertEqual(country,    address.country)
        self.assertEqual(department, address.department)

    def test_editview(self):
        orga = self.orga

        name = 'Address#1'
        address_value = '21 jump street'
        po_box = 'Popop'
        city = 'Antlantis'
        state = '??'
        zipcode = '424242'
        country = 'wtf'
        department = 'rucrazy'

        self._create_address(orga, name, address_value, po_box, city, state, zipcode, country, department)
        address = Address.objects.filter(object_id=orga.id)[0]

        url = '/persons/address/edit/%s' % address.id
        self.assertEqual(200, self.client.get(url).status_code)

        city = 'Groville'
        country = 'Groland'
        response = self.client.post(url, data={'name':       name,
                                               'address':    address,
                                               'po_box':     po_box,
                                               'city':       city,
                                               'state':      state,
                                               'zipcode':    zipcode,
                                               'country':    country,
                                               'department': department,
                                             }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        address = self.refresh(address)
        self.assertEqual(city,    address.city)
        self.assertEqual(country, address.country)

    def test_deleteview(self):
        orga = self.orga

        self._create_address(orga, 'name', 'address', 'po_box', 'city', 'state', 'zipcode', 'country', 'department')
        address = Address.objects.filter(object_id=orga.id)[0]
        ct = ContentType.objects.get_for_model(Address)

        response = self.client.post('/creme_core/entity/delete_related/%s' % ct.id, data={'id': address.id})
        self.assertEqual(0, Address.objects.filter(object_id=orga.id).count())
