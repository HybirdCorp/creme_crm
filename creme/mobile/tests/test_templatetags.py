from django.template import Context, Template
from django.test.client import RequestFactory
from django.urls.base import reverse
from parameterized import parameterized

from creme.activities import constants as act_constants
from creme.activities.models import Status
from creme.creme_core.models import FieldsConfig
from creme.creme_core.tests.base import (
    OverrideSettingValueContext,
    skipIfNotInstalled,
)
from creme.mobile import setting_keys
from creme.mobile.templatetags.mobile_tags import (
    mobile_activity_in_progress,
    mobile_document_class,
    mobile_location_map_url,
)
from creme.mobile.tests.base import MobileBaseTestCase
from creme.persons import get_address_model, get_contact_model

Address = get_address_model()
Contact = get_contact_model()


class MobileTemplatetagsTestCase(MobileBaseTestCase):
    @staticmethod
    def create_address(user):
        return Address.objects.create(
            address='154 hopper avenue',
            zipcode='61045',
            city='Fair Lawn',
            state='New Jersey',
            country='USA',
            owner=Contact.objects.create(
                user=user,
                first_name='Henri',
                last_name='Krinkle'
            )
        )

    @parameterized.expand([
        ('google/maps?q={search}',
         'google/maps?q=154+hopper+avenue+61045+Fair+Lawn'),
        ('google/maps/place?{lat},{lng}', 'google/maps/place?,'),
        ('osm/place?q={search}&mlat={lat}&mlng={lng}',
         'osm/place?q=154+hopper+avenue+61045+Fair+Lawn&mlat=&mlng='),
        ('google/maps', 'google/maps'),
    ])
    @skipIfNotInstalled('creme.geolocation')
    def test_mobile_location_map_url(self, pattern, expected):
        user = self.login_as_root_and_get()
        address = self.create_address(user)

        with OverrideSettingValueContext(setting_keys.location_map_url_key, pattern):
            self.assertEqual(mobile_location_map_url(address), expected)

    @parameterized.expand([
        ('google/maps?q={search}',
         'google/maps?q=154+hopper+avenue+61045+Fair+Lawn'),
        ('google/maps/place?{lat},{lng}', 'google/maps/place?42.33,5.28'),
        ('osm/place?q={search}&mlat={lat}&mlng={lng}',
         'osm/place?q=154+hopper+avenue+61045+Fair+Lawn&mlat=42.33&mlng=5.28'),
        ('google/maps', 'google/maps'),
    ])
    @skipIfNotInstalled('creme.geolocation')
    def test_mobile_location_map_url_geoaddress(self, pattern, expected):
        from creme.geolocation.models import GeoAddress

        user = self.login_as_root_and_get()
        address = self.create_address(user)

        address.geoaddress.status = GeoAddress.Status.COMPLETE
        address.geoaddress.latitude = 42.33
        address.geoaddress.longitude = 5.28
        address.geoaddress.save()

        with OverrideSettingValueContext(setting_keys.location_map_url_key, pattern):
            self.assertEqual(mobile_location_map_url(address), expected)

    @parameterized.expand([
        ('Android', 'android'),
        ('Android-10+', 'android'),
        ('Ipad', 'ios'),
        ('IPHONE', 'ios'),
        ('IOS', 'all'),
    ])
    def test_document_class(self, useragent, expected):
        request = RequestFactory().get(reverse('mobile__portal'))
        request.META['HTTP_USER_AGENT'] = useragent

        self.assertEqual(mobile_document_class(request), expected)

    def test_prepare_fields(self):
        user = self.get_root_user()
        FieldsConfig.objects.create(
            content_type=Contact,
            descriptions=[('phone', {FieldsConfig.HIDDEN: True})],
        )
        contact = Contact.objects.create(
            user=user,
            first_name='Henri', last_name='Krinkle',
            phone='123456', email='henri@foo.com',
        )

        with self.assertNoException():
            template = Template(
                r"{% load mobile_tags %}"
                r"{% mobile_prepare_fields object 'email' 'phone' %}"
                r"{{object.last_name}}#{{object.email}}#{{object.phone|default:'—'}}"
            )
            render = template.render(Context(self.build_context(user=user, instance=contact)))

        self.assertEqual('Krinkle#henri@foo.com#—', render.strip())

    def test_activity_type_str__meeting(self):
        user = self.get_root_user()
        meeting = self._create_meeting(user=user, title='Meeting #1')

        with self.assertNoException():
            template = Template(
                r'{% load mobile_tags %}'
                r'<div class="activity-type-{{activity|mobile_activity_type_str}}" />'
            )
            render = template.render(Context({'activity': meeting}))

        self.assertEqual(
            '<div class="activity-type-meeting" />',
            render.strip(),
        )

    def test_activity_type_str__phonecall(self):
        user = self.get_root_user()
        meeting = self._create_pcall(user=user, title='Call #1')

        with self.assertNoException():
            template = Template(
                r'{% load mobile_tags %}'
                r'<div class="activity-type-{{activity|mobile_activity_type_str}}" />'
            )
            render = template.render(Context({'activity': meeting}))

        self.assertEqual(
            '<div class="activity-type-phonecall" />',
            render.strip(),
        )

    def test_activity_in_progress(self):
        user = self.get_root_user()
        activity = self._create_pcall(user=user, title='Call #1')
        self.assertIsNone(activity.status)
        self.assertIs(mobile_activity_in_progress(activity), False)

        activity.status = self.get_object_or_fail(
            Status, uuid=act_constants.UUID_STATUS_DONE,
        )
        self.assertIs(mobile_activity_in_progress(activity), False)

        activity.status = self.get_object_or_fail(
            Status, uuid=act_constants.UUID_STATUS_IN_PROGRESS,
        )
        self.assertIs(mobile_activity_in_progress(activity), True)

# TODO:
#  - mobile_organisation_subjects
#  - mobile_activity_card
#  - mobile_footer
