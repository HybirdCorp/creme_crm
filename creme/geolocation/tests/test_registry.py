from creme.creme_core.utils.media import creme_media_themed_url
from creme.geolocation.registry import GeoMarkerIcon, GeoMarkerIconRegistry
from creme.persons import get_contact_model, get_organisation_model

from .base import GeoLocationBaseTestCase

Contact = get_contact_model()
Organisation = get_organisation_model()


class MarkerIconRegistryTestCase(GeoLocationBaseTestCase):
    def test_register(self):
        registry = GeoMarkerIconRegistry()
        self.assertEqual(registry.icon_for_model(Contact), GeoMarkerIcon())

        registry.register(Contact, GeoMarkerIcon(path='images/marker-A.jpg'))

        self.assertEqual(
            registry.icon_for_model(Contact),
            GeoMarkerIcon(path='images/marker-A.jpg')
        )

        registry.register(Contact, 'images/marker-B.jpg')
        self.assertEqual(
            registry.icon_for_model(Contact),
            GeoMarkerIcon(path='images/marker-B.jpg')
        )

    def test_for_model(self):
        registry = GeoMarkerIconRegistry()

        self.assertEqual(registry.icon_for_model(Contact), GeoMarkerIcon())
        self.assertEqual(registry.icon_for_model(Contact).url, '')

        registry.register(Contact, GeoMarkerIcon('images/marker-A.jpg'))

        self.assertEqual(
            registry.icon_for_model(Contact),
            GeoMarkerIcon(path='images/marker-A.jpg')
        )
        self.assertEqual(registry.icon_for_model(Contact).url, '')

        registry.register(Contact, GeoMarkerIcon('geolocation/images/marker-icon.png'))

        self.assertEqual(
            registry.icon_for_model(Contact),
            GeoMarkerIcon(path='geolocation/images/marker-icon.png')
        )
        self.assertEqual(
            registry.icon_for_model(Contact).url,
            creme_media_themed_url('geolocation/images/marker-icon.png')
        )

    def test_for_instance(self):
        user = self.get_root_user()
        orga = Organisation.objects.create(name='Orga 1', user=user)

        registry = GeoMarkerIconRegistry()

        self.assertEqual(registry.icon_for_instance(orga), GeoMarkerIcon())
        self.assertEqual(registry.icon_for_instance(orga).url, '')

        registry.register(Organisation, GeoMarkerIcon('images/marker-A.jpg'))

        self.assertEqual(
            registry.icon_for_instance(orga),
            GeoMarkerIcon(path='images/marker-A.jpg')
        )
        self.assertEqual(registry.icon_for_instance(orga).url, '')

        registry.register(Organisation, GeoMarkerIcon('geolocation/images/marker-icon.png'))

        self.assertEqual(
            registry.icon_for_instance(orga),
            GeoMarkerIcon(path='geolocation/images/marker-icon.png')
        )
        self.assertEqual(
            registry.icon_for_instance(orga).url,
            creme_media_themed_url('geolocation/images/marker-icon.png'),
        )
