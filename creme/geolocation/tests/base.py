from creme.creme_core.tests.base import CremeTestCase
from creme.persons import (
    get_address_model,
    get_contact_model,
    get_organisation_model,
)

from ..models import GeoAddress, Town

Address = get_address_model()
Contact = get_contact_model()
Organisation = get_organisation_model()


class GeoLocationBaseTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Town.objects.all().delete()  # TODO: backup ?

    def assertModelInstance(self, instance, klass, **kwargs):
        self.assertIsInstance(instance, klass)

        for key, expected in kwargs.items():
            value = str(getattr(instance, key))
            expected_str = str(expected)
            self.assertEqual(
                value, expected_str,
                f'unexpected {klass.__name__}.{key} value: {value} != {expected_str}'
            )

    def assertGeoAddress(self, instance, **kwargs):
        self.assertModelInstance(instance, GeoAddress, **kwargs)

    def assertListAddressAsDict(self, addresses, *expected):
        def key(a):
            return a['id']

        self.assertListEqual(sorted(addresses, key=key), sorted(expected, key=key))

    @staticmethod
    def create_address(owner,
                       address='27 bis rue du yahourt',
                       zipcode='13008',
                       town='Marseille',
                       geoloc=None,
                       ):
        address = Address.objects.create(
            name=address,
            address=address,
            po_box='',
            zipcode=zipcode,
            city=town,
            department=zipcode[:2],
            state='',
            country='',
            owner=owner,
        )

        if geoloc is not None:
            latitude, longitude = geoloc
            address.geoaddress.status = GeoAddress.Status.COMPLETE
            address.geoaddress.latitude = latitude
            address.geoaddress.longitude = longitude
            address.geoaddress.save()

        return address

    def create_billing_address(self,
                               owner,
                               address='27 bis rue du yahourt',
                               zipcode='13008',
                               town='Marseille',
                               geoloc=None,
                               ):
        owner.billing_address = address = self.create_address(
            owner, address, zipcode, town, geoloc
        )
        owner.save()

        return self.refresh(address)

    def create_shipping_address(self,
                                owner,
                                address='27 bis rue du yahourt',
                                zipcode='13008',
                                town='Marseille',
                                geoloc=None,
                                ):
        owner.shipping_address = address = self.create_address(
            owner, address, zipcode, town, geoloc,
        )
        owner.save()

        return self.refresh(address)
