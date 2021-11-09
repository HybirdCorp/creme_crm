# -*- coding: utf-8 -*-

from django.conf import settings
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.core.entity_filter import condition_handler, operators
from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickHomeLocation,
    EntityFilter,
)
from creme.creme_core.tests.base import OverrideSettingValueContext
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.persons.constants import FILTER_CONTACT_ME, FILTER_MANAGED_ORGA
from creme.persons.tests.base import (
    skipIfCustomAddress,
    skipIfCustomContact,
    skipIfCustomOrganisation,
)

from .. import setting_keys
from ..bricks import (
    GoogleDetailMapBrick,
    GoogleFilteredMapBrick,
    GoogleNeighboursMapBrick,
    OpenStreetMapDetailMapBrick,
    OpenStreetMapFilteredMapBrick,
    OpenStreetMapNeighboursMapBrick,
    _MapBrick,
)
from .base import Contact, GeoLocationBaseTestCase, Organisation


@skipIfCustomContact
@skipIfCustomOrganisation
class MapBrickTestCase(BrickTestCaseMixin, GeoLocationBaseTestCase):
    def setUp(self):
        super().setUp()
        self.login()
        self.brick = _MapBrick()

        self.contacts_title      = str(Contact._meta.verbose_name_plural)
        self.organisations_title = str(Organisation._meta.verbose_name_plural)

    @staticmethod
    def create_filter(pk, name, owner, model, field, operator, *values):
        return EntityFilter.objects.smart_update_or_create(
            pk, name, model=model,
            user=owner,
            is_private=True, is_custom=True,
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=model,
                    operator=operator,
                    field_name=field, values=values,
                ),
            ],
        )

    def test_api_key(self):
        with OverrideSettingValueContext(setting_keys.GOOGLE_API_KEY, 'thegoldenticket'):
            self.assertEqual(_MapBrick().get_api_key(), '')
            self.assertEqual(OpenStreetMapDetailMapBrick().get_api_key(), '')
            self.assertEqual(GoogleDetailMapBrick().get_api_key(), 'thegoldenticket')

    def test_map_settings(self):
        self.assertEqual(_MapBrick().get_map_settings(), {})
        self.assertDictEqual(OpenStreetMapDetailMapBrick().get_map_settings(), {
            'nominatim_url': settings.GEOLOCATION_OSM_NOMINATIM_URL,
            'tilemap_url': settings.GEOLOCATION_OSM_TILEMAP_URL,
            'copyright_url': settings.GEOLOCATION_OSM_COPYRIGHT_URL,
            'copyright_title': settings.GEOLOCATION_OSM_COPYRIGHT_TITLE,
        })
        self.assertEqual(GoogleDetailMapBrick().get_map_settings(), {})

    def test_filter_choices01(self):
        user = self.user
        self.assertListEqual([], self.brick.get_filter_choices(user))

        get_efilter = EntityFilter.objects.get
        contact_me    = get_efilter(pk=FILTER_CONTACT_ME)
        managed_orgas = get_efilter(pk=FILTER_MANAGED_ORGA)

        contact_group = (
            self.contacts_title,
            [(contact_me.pk, f'{self.contacts_title} - {contact_me.name}')],
        )
        self.assertListEqual(
            [contact_group],
            self.brick.get_filter_choices(user, Contact),
        )

        orga_group = (
            self.organisations_title,
            [(managed_orgas.pk, f'{self.organisations_title} - {managed_orgas.name}')]
        )
        self.assertListEqual(
            [orga_group],
            self.brick.get_filter_choices(user, Organisation),
        )
        self.assertListEqual(
            [contact_group, orga_group],
            self.brick.get_filter_choices(user, Contact, Organisation),
        )

    def test_filter_choices02(self):
        user = self.user

        get_efilter = EntityFilter.objects.get
        contact_me    = get_efilter(pk=FILTER_CONTACT_ME)
        managed_orgas = get_efilter(pk=FILTER_MANAGED_ORGA)

        EQUALS = operators.EQUALS
        efilter1 = self.create_filter(
            'filter-1', 'Contact filter', user, Contact, 'first_name', EQUALS, 'John',
        )
        efilter2 = self.create_filter(
            'filter-2', 'Orga filter', user, Organisation, 'name', EQUALS, 'Le spectre',
        )

        self.assertEqual([], self.brick.get_filter_choices(user))

        contact_group = self.brick.get_filter_choices(user, Contact)[0]
        contacts_title = self.contacts_title
        self.assertEqual(contacts_title, contact_group[0])

        contact_opt = contact_group[1]
        self.assertInChoices(
            value=contact_me.pk,
            label=f'{contacts_title} - {contact_me.name}',
            choices=contact_opt,
        )
        self.assertInChoices(
            value=efilter1.pk,
            label=f'{contacts_title} - {efilter1.name}',
            choices=contact_opt,
        )

        # -----
        orga_group = self.brick.get_filter_choices(user, Organisation)[0]
        orgas_title = self.organisations_title
        self.assertEqual(orgas_title, orga_group[0])

        orga_opt = orga_group[1]
        self.assertInChoices(
            value=managed_orgas.pk,
            label=f'{orgas_title} - {managed_orgas.name}',
            choices=orga_opt,
        )
        self.assertInChoices(
            value=efilter2.pk,
            label=f'{orgas_title} - {efilter2.name}',
            choices=orga_opt,
        )

        # -----
        self.assertListEqual(
            [contact_group, orga_group],
            self.brick.get_filter_choices(user, Contact, Organisation)
        )

    def test_filter_choices_private(self):
        user = self.user
        other_user = self.other_user

        managed_orgas = EntityFilter.objects.get(pk=FILTER_MANAGED_ORGA)
        efilter = self.create_filter(
            'filter-2', 'Orga filter', other_user, Organisation, 'name',
            operators.EQUALS, 'Le spectre',
        )

        title = self.organisations_title
        self.assertListEqual(
            [
                (
                    title,
                    [(managed_orgas.pk, f'{title} - {managed_orgas.name}')],
                )
            ],
            self.brick.get_filter_choices(user, Organisation),
        )

        orga_group = self.brick.get_filter_choices(other_user, Organisation)[0]
        self.assertEqual(title, orga_group[0])

        orga_opt = orga_group[1]
        self.assertInChoices(
            value=managed_orgas.pk,
            label=f'{title} - {managed_orgas.name}',
            choices=orga_opt,
        )
        self.assertInChoices(
            value=efilter.pk,
            label=f'{title} - {efilter.name}',
            choices=orga_opt,
        )

    @skipIfCustomAddress
    def test_google_detail(self):
        contact = self.user.linked_contact
        self.create_address(contact)

        BrickDetailviewLocation.objects.create_if_needed(
            brick=GoogleDetailMapBrick,
            model=type(contact),
            order=50,
            zone=BrickDetailviewLocation.BOTTOM,
        )

        api_key = 'thegoldenticket'
        with OverrideSettingValueContext(setting_keys.GOOGLE_API_KEY, api_key):
            response = self.assertGET200(contact.get_absolute_url())

        self.assertTemplateUsed(response, 'geolocation/bricks/google/detail-map.html')

        tree = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(tree, GoogleDetailMapBrick.id_)
        self.assertEqual(_('Map'), self.get_brick_title(brick_node))

        script_node = self.get_html_node_or_fail(
            brick_node, './/script[@type="text/javascript"]',
        )
        self.assertIn(f"apiKey: '{api_key}'", script_node.text)

    @skipIfCustomAddress
    def test_osm_detail(self):
        contact = self.user.linked_contact
        self.create_address(contact)

        BrickDetailviewLocation.objects.create_if_needed(
            brick=OpenStreetMapDetailMapBrick,
            model=type(contact),
            order=50,
            zone=BrickDetailviewLocation.BOTTOM,
        )

        nominatim_url = 'https://nominatim.openstreetmap.org/search'
        tilemap_url = '{s}othermap.com/{x}/{y}/{z}.jpeg'
        cright_url = '{s}othermap.com/copyright'
        cright_title = 'OpenStreetMap contributors'

        with override_settings(
            GEOLOCATION_OSM_NOMINATIM_URL=nominatim_url,
            GEOLOCATION_OSM_TILEMAP_URL=tilemap_url,
            GEOLOCATION_OSM_COPYRIGHT_URL=cright_url,
            GEOLOCATION_OSM_COPYRIGHT_TITLE=cright_title,
        ):
            response = self.assertGET200(contact.get_absolute_url())

        self.assertTemplateUsed(response, 'geolocation/bricks/osm/detail-map.html')

        tree = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(tree, OpenStreetMapDetailMapBrick.id_)
        self.assertEqual(_('Map'), self.get_brick_title(brick_node))

        script_node = self.get_html_node_or_fail(
            brick_node, './/script[@type="text/javascript"]',
        )
        self.assertIn(f"nominatimUrl: '{nominatim_url}'", script_node.text)
        self.assertIn(f"tileMapUrl: '{tilemap_url}'", script_node.text)
        self.assertIn(
            f"""tileMapAttribution: '&copy; <a href="{cright_url}">{cright_title}</a>'""",
            script_node.text,
        )

    def test_google_filtered(self):
        BrickHomeLocation.objects.get_or_create(
            brick_id=GoogleFilteredMapBrick.id_,
            defaults={'order': 50},
        )

        api_key = 'thegoldenticket'
        with OverrideSettingValueContext(setting_keys.GOOGLE_API_KEY, api_key):
            response = self.assertGET200(reverse('creme_core__home'))

        self.assertTemplateUsed(response, 'geolocation/bricks/google/filtered-map.html')

        tree = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(tree, GoogleFilteredMapBrick.id_)
        self.assertEqual(_('Maps By Filter'), self.get_brick_title(brick_node))

        script_node = self.get_html_node_or_fail(
            brick_node, './/script[@type="text/javascript"]',
        )
        self.assertIn(f"apiKey: '{api_key}'", script_node.text)

    def test_osm_filtered(self):
        BrickHomeLocation.objects.get_or_create(
            brick_id=OpenStreetMapFilteredMapBrick.id_,
            defaults={'order': 50},
        )

        nominatim_url = 'https://nominatim.openstreetmap.org/search'
        tilemap_url = '{s}othermap.com/{x}/{y}/{z}.jpeg'
        cright_url = '{s}othermap.com/copyright'
        cright_title = 'OpenStreetMap contributors'

        with override_settings(
            GEOLOCATION_OSM_NOMINATIM_URL=nominatim_url,
            GEOLOCATION_OSM_TILEMAP_URL=tilemap_url,
            GEOLOCATION_OSM_COPYRIGHT_URL=cright_url,
            GEOLOCATION_OSM_COPYRIGHT_TITLE=cright_title,
        ):
            response = self.assertGET200(reverse('creme_core__home'))

        self.assertTemplateUsed(response, 'geolocation/bricks/osm/filtered-map.html')

        tree = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(tree, OpenStreetMapFilteredMapBrick.id_)
        self.assertEqual(_('Maps By Filter'), self.get_brick_title(brick_node))

        script_node = self.get_html_node_or_fail(
            brick_node, './/script[@type="text/javascript"]',
        )
        self.assertIn(f"nominatimUrl: '{nominatim_url}'", script_node.text)
        self.assertIn(f"tileMapUrl: '{tilemap_url}'", script_node.text)
        self.assertIn(
            f"""tileMapAttribution: '&copy; <a href="{cright_url}">{cright_title}</a>'""",
            script_node.text,
        )

    @skipIfCustomAddress
    def test_google_neighbours(self):
        contact = self.user.linked_contact
        self.create_address(contact)

        BrickDetailviewLocation.objects.create_if_needed(
            brick=GoogleNeighboursMapBrick,
            model=type(contact),
            order=50,
            zone=BrickDetailviewLocation.BOTTOM,
        )

        api_key = 'thegoldenticket'
        with OverrideSettingValueContext(setting_keys.GOOGLE_API_KEY, api_key):
            response = self.assertGET200(contact.get_absolute_url())

        self.assertTemplateUsed(response, 'geolocation/bricks/google/neighbours-map.html')

        tree = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(tree, GoogleNeighboursMapBrick.id_)
        self.assertEqual(_('Around this place'), self.get_brick_title(brick_node))

        script_node = self.get_html_node_or_fail(
            brick_node, './/script[@type="text/javascript"]',
        )
        self.assertIn(f"apiKey: '{api_key}'", script_node.text)

    @skipIfCustomAddress
    def test_osm_neighbours(self):
        contact = self.user.linked_contact
        self.create_address(contact)

        BrickDetailviewLocation.objects.create_if_needed(
            brick=OpenStreetMapNeighboursMapBrick,
            model=type(contact),
            order=50,
            zone=BrickDetailviewLocation.BOTTOM,
        )

        nominatim_url = 'https://nominatim.openstreetmap.org/search'
        tilemap_url = '{s}othermap.com/{x}/{y}/{z}.jpeg'
        cright_url = '{s}othermap.com/copyright'
        cright_title = 'OpenStreetMap contributors'

        with override_settings(
            GEOLOCATION_OSM_NOMINATIM_URL=nominatim_url,
            GEOLOCATION_OSM_TILEMAP_URL=tilemap_url,
            GEOLOCATION_OSM_COPYRIGHT_URL=cright_url,
            GEOLOCATION_OSM_COPYRIGHT_TITLE=cright_title,
        ):
            response = self.assertGET200(contact.get_absolute_url())

        self.assertTemplateUsed(response, 'geolocation/bricks/osm/neighbours-map.html')

        tree = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(tree, OpenStreetMapNeighboursMapBrick.id_)
        self.assertEqual(_('Around this place'), self.get_brick_title(brick_node))

        script_node = self.get_html_node_or_fail(
            brick_node, './/script[@type="text/javascript"]',
        )
        self.assertIn(f"nominatimUrl: '{nominatim_url}'", script_node.text)
        self.assertIn(f"tileMapUrl: '{tilemap_url}'", script_node.text)
        self.assertIn(
            f"""tileMapAttribution: '&copy; <a href="{cright_url}">{cright_title}</a>'""",
            script_node.text,
        )
