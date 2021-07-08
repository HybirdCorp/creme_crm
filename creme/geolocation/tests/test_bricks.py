# -*- coding: utf-8 -*-

from django.conf import settings

from creme.creme_core.core.entity_filter import condition_handler, operators
from creme.creme_core.models.entity_filter import EntityFilter
from creme.creme_core.tests.base import OverrideSettingValueContext
from creme.geolocation.bricks import (
    GoogleDetailMapBrick,
    OpenStreetMapDetailMapBrick,
)
from creme.persons.constants import FILTER_CONTACT_ME, FILTER_MANAGED_ORGA
from creme.persons.tests.base import (
    skipIfCustomContact,
    skipIfCustomOrganisation,
)

from .. import setting_keys
from ..bricks import _MapBrick
from .base import Contact, GeoLocationBaseTestCase, Organisation


@skipIfCustomContact
@skipIfCustomOrganisation
class MapBrickTestCase(GeoLocationBaseTestCase):
    def setUp(self):
        super().setUp()
        self.login()
        self.brick = _MapBrick()

        self.contacts_title      = str(Contact._meta.verbose_name_plural)
        self.organisations_title = str(Organisation._meta.verbose_name_plural)

    def create_filter(self, pk, name, owner, model, field, operator, *values):
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
        self.assertEqual([], self.brick.get_filter_choices(user))

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
