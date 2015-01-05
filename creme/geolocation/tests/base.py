# -*- coding: utf-8 -*-

try:
    from creme.creme_core.utils import safe_unicode
    from creme.creme_core.tests.base import CremeTestCase

    from creme.persons.models.address import Address

    from ..models import GeoAddress, Town
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class GeoLocationBaseTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'persons')
        Town.objects.all().delete()

    def assertModelInstance(self, instance, klass, **kwargs):
        self.assertIsInstance(instance, klass)

        for key, expected in kwargs.iteritems():
            value = getattr(instance, key)
            self.assertEqual(safe_unicode(value), safe_unicode(expected),
                             u'unexpected %s.%s value : %s != %s' % (klass.__name__, key,
                                                                     safe_unicode(value),
                                                                     safe_unicode(expected)))

    def assertGeoAddress(self, instance, **kwargs):
        self.assertModelInstance(instance, GeoAddress, **kwargs)

    def create_address(self, owner, address='13 rue du yahourt', zipcode='13008', town='Marseille', geoloc=None):
        address = Address.objects.create(name=address,
                                         address=address,
                                         po_box='',
                                         zipcode=zipcode,
                                         city=town,
                                         department=zipcode[:2],
                                         state=None,
                                         country='',
                                         owner=owner
                                        )

        if geoloc is not None:
            latitude, longitude = geoloc
            address.geoaddress.latitude = latitude
            address.geoaddress.longitude = longitude
            address.geoaddress.save()

        return address

    def create_billing_address(self, owner, address='13 rue du yahourt', zipcode='13008', town='Marseille', geoloc=None):
        owner.billing_address = self.create_address(owner, address, zipcode, town, geoloc)
        owner.save()
        return Address.objects.get(pk=owner.billing_address.pk)

    def create_shipping_address(self, owner, address='13 rue du yahourt', zipcode='13008', town='Marseille', geoloc=None):
        owner.shipping_address = self.create_address(owner, address, zipcode, town, geoloc)
        owner.save()
        return Address.objects.get(pk=owner.shipping_address.pk)

