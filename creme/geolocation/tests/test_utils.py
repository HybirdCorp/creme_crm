# -*- coding: utf-8 -*-

try:
    from django.utils.translation import ugettext as _

    from creme.creme_core.models import SettingValue

    from creme.persons.tests.base import (skipIfCustomAddress,
            skipIfCustomContact, skipIfCustomOrganisation)

    from .. import constants, setting_keys
    from ..models import GeoAddress
    from ..utils import (get_setting, get_radius, get_google_api_key, address_as_dict,
             addresses_from_persons, location_bounding_box)
    from .base import GeoLocationBaseTestCase, Organisation, Contact, Address
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class GeoLocationUtilsTestCase(GeoLocationBaseTestCase):
    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_address_as_dict(self):
        user = self.login()

        orga = Organisation.objects.create(name='Orga 1', user=user)
        address = self.create_address(orga, zipcode='13012', town=u'Marseille', geoloc=(43.299991, 5.364832))

        self.assertDictEqual(dict(id=address.pk,
                                  content=u'13 rue du yahourt 13012 Marseille 13',
                                  title=u'13 rue du yahourt',
                                  owner=u'Orga 1',
                                  is_shipping=False,
                                  is_billing=False,
                                  is_complete=True,
                                  latitude=43.299991,
                                  longitude=5.364832,
                                  draggable=True,
                                  geocoded=False,
                                  status_label='',
                                  status=GeoAddress.COMPLETE,
                                  url=orga.get_absolute_url(),
                                 ),
                             address_as_dict(address)
                            )

    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_address_as_dict_empty_billing_shipping(self):
        user = self.login()

        orga = Organisation.objects.create(name='Orga 1', user=user)
        address = self.create_billing_address(orga, address='', zipcode='', town='', geoloc=(43.299991, 5.364832))

        self.assertDictEqual(dict(id=address.pk,
                                  content=u'',
                                  title=_(u'Billing address'),
                                  owner=u'Orga 1',
                                  is_shipping=False,
                                  is_billing=True,
                                  is_complete=True,
                                  latitude=43.299991,
                                  longitude=5.364832,
                                  draggable=True,
                                  geocoded=False,
                                  status_label='',
                                  status=GeoAddress.COMPLETE,
                                  url=orga.get_absolute_url(),
                                 ),
                             address_as_dict(address)
                            )

        address = self.create_shipping_address(orga, address='', zipcode='', town='', geoloc=(43.299991, 5.364832))

        self.assertDictEqual(dict(id=address.pk,
                                  content=u'',
                                  title=_(u'Shipping address'),
                                  owner=u'Orga 1',
                                  is_shipping=True,
                                  is_complete=True,
                                  is_billing=False,
                                  latitude=43.299991,
                                  longitude=5.364832,
                                  draggable=True,
                                  geocoded=False,
                                  status_label='',
                                  status=GeoAddress.COMPLETE,
                                  url=orga.get_absolute_url(),
                                 ),
                             address_as_dict(address)
                            )

    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_address_as_dict_empty(self):
        user = self.login()

        orga = Organisation.objects.create(name='Orga 1', user=user)
        address = self.create_address(orga, address='', zipcode='', town='', geoloc=(43.299991, 5.364832))

        self.assertDictEqual(dict(id=address.pk,
                                  content=u'',
                                  title=u'',
                                  owner=u'Orga 1',
                                  is_shipping=False,
                                  is_billing=False,
                                  is_complete=True,
                                  latitude=43.299991,
                                  longitude=5.364832,
                                  draggable=True,
                                  geocoded=False,
                                  status_label='',
                                  status=GeoAddress.COMPLETE,
                                  url=orga.get_absolute_url()
                                 ),
                             address_as_dict(address)
                            )

    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_address_as_dict_missing_geoaddress01(self):
        user = self.login()

        orga = Organisation.objects.create(name='Orga 1', user=user)
        address = self.create_address(orga, address='', zipcode='', town='', geoloc=(43.299991, 5.364832))
        GeoAddress.objects.filter(address=address).delete()

        address = self.refresh(address)

        with self.assertRaises(GeoAddress.DoesNotExist):
            address.geoaddress

        self.assertDictEqual(dict(id=address.pk,
                                  content=u'',
                                  title=u'',
                                  owner=u'Orga 1',
                                  is_shipping=False,
                                  is_billing=False,
                                  is_complete=False,
                                  latitude=None,
                                  longitude=None,
                                  draggable=True,
                                  geocoded=False,
                                  status_label=_('Not localized'),
                                  status=GeoAddress.UNDEFINED,
                                  url=orga.get_absolute_url(),
                                 ),
                             address_as_dict(address)
                            )

    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_address_as_dict_missing_geoaddress02(self):
        "With select_related"
        user = self.login()

        orga = Organisation.objects.create(name='Orga 1', user=user)
        address = self.create_address(orga, address='', zipcode='', town='', geoloc=(43.299991, 5.364832))
        GeoAddress.objects.filter(address=address).delete()
        address = Address.objects.select_related('geoaddress').get(pk=address.pk)

        with self.assertRaises(GeoAddress.DoesNotExist):
            address.geoaddress

        self.assertDictEqual(dict(id=address.pk,
                                  content=u'',
                                  title=u'',
                                  owner=u'Orga 1',
                                  is_shipping=False,
                                  is_billing=False,
                                  is_complete=False,
                                  latitude=None,
                                  longitude=None,
                                  draggable=True,
                                  geocoded=False,
                                  status_label=_('Not localized'),
                                  status=GeoAddress.UNDEFINED,
                                  url=orga.get_absolute_url(),
                                 ),
                             address_as_dict(address)
                            )

    @skipIfCustomOrganisation
    @skipIfCustomContact
    def test_addresses_from_persons(self):
        user = self.login()

        orga    = Organisation.objects.create(name='Orga 1', user=user)
        orga2   = Organisation.objects.create(name='Orga 2', user=user)
        contact = Contact.objects.create(last_name='Contact 1', user=user)

        orga_address = self.create_billing_address(orga, zipcode='13012', town=u'Marseille')
        self.create_shipping_address(orga, zipcode='01190', town=u'Ozan')
        self.create_address(orga, zipcode='01630', town=u'Péron')

        orga2_address = self.create_shipping_address(orga2, zipcode='01190', town=u'Ozan')
        self.create_address(orga2, zipcode='01630', town=u'Péron')

        contact_address = self.create_address(contact, zipcode='01630', town=u'Péron')
        self.assertListEqual(list(addresses_from_persons(Contact.objects.all(), user)),
                             [contact_address]
                            )

        self.assertListEqual(sorted(list(addresses_from_persons(Organisation.objects.all(), user)), key=lambda a: a.pk),
                             sorted([orga_address, orga2_address], key=lambda a: a.pk)
                            )

    def test_get_setting(self):
        self.assertIsNone(get_setting('unknown'))
        self.assertEqual(get_setting('unknown', 12), 12)
        self.assertEqual(get_setting(setting_keys.NEIGHBOURHOOD_DISTANCE, constants.DEFAULT_SEPARATING_NEIGHBOURS),
                         constants.DEFAULT_SEPARATING_NEIGHBOURS
                        )

        setting = SettingValue.objects.get_or_create(key_id=setting_keys.NEIGHBOURHOOD_DISTANCE.id)[0]

        new_value = 12500
        setting.value = new_value
        setting.save()
        self.assertEqual(get_setting(setting_keys.NEIGHBOURHOOD_DISTANCE, constants.DEFAULT_SEPARATING_NEIGHBOURS),
                         new_value
                        )

    def test_get_radius(self):
        self.assertEqual(get_radius(), constants.DEFAULT_SEPARATING_NEIGHBOURS)

        setting = SettingValue.objects.get_or_create(key_id=setting_keys.NEIGHBOURHOOD_DISTANCE.id)[0]

        new_value = 12500
        setting.value = new_value
        setting.save()
        self.assertEqual(get_radius(), new_value)

    def test_get_google_api_key(self):
        self.assertEqual(get_google_api_key(), '')

        setting = SettingValue.objects.get_or_create(key_id=setting_keys.GOOGLE_API_KEY.id)[0]

        new_value = '12500'
        setting.value = new_value
        setting.save()
        self.assertEqual(get_google_api_key(), new_value)

    def test_location_bounding_box(self):
        # 10 km ~ 0.09046499004885108 lat, 0.12704038469036066 long (for 45° lat)
        self.assertEqual(((45.0 - 0.09046499004885108, 5.0 - 0.12704038469036066),
                          (45.0 + 0.09046499004885108, 5.0 + 0.12704038469036066),
                         ),
                         location_bounding_box(45.0, 5.0, 10000)
                        )

        # 10 km ~ 0.09046499004885108 lat, 0.09559627851921597 long (for 20° lat)
        self.assertEqual(((20.0 - 0.09046499004885108, 5.0 - 0.09559627851921597),
                          (20.0 + 0.09046499004885108, 5.0 + 0.09559627851921597),
                         ),
                         location_bounding_box(20.0, 5.0, 10000)
                        )
