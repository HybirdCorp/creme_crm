################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014-2025  Hybird
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

import logging

from django.contrib.auth import get_user_model

from creme import persons
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickMypageLocation,
    SettingValue,
)

from . import bricks, constants, setting_keys
from .management.commands.geolocation import Command as GeolocationCommand

logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core', 'persons']

    SETTING_VALUES = [
        SettingValue(key=setting_keys.use_entity_icon_key, value=False),
        SettingValue(key=setting_keys.google_api_key, value=''),
        SettingValue(
            key=setting_keys.neighbourhood_distance_key,
            value=constants.DEFAULT_SEPARATING_NEIGHBOURS,
        ),
    ]

    def _already_populated(self):
        return SettingValue.objects.exists_4_key(
            setting_keys.neighbourhood_distance_key
        )

    def _first_populate(self):
        super()._first_populate()
        self._populate_towns()

    def _populate_towns(self):
        if self.verbosity:
            self.stdout.write('\n ', ending='')
            self.stdout.flush()

        GeolocationCommand().import_town_all(verbosity=self.verbosity)

    def _populate_bricks_config_for_persons(self):
        for model in (persons.get_organisation_model(), persons.get_contact_model()):
            BrickDetailviewLocation.objects.multi_create(
                defaults={'model': model},
                data=[
                    {
                        'brick': bricks.OpenStreetMapDetailMapBrick, 'order': 70,
                        'zone': BrickDetailviewLocation.LEFT,
                    }, {
                        'brick': bricks.OpenStreetMapNeighboursMapBrick, 'order': 600,
                        'zone': BrickDetailviewLocation.BOTTOM,
                    },
                ],
            )

    def _populate_bricks_config_for_mypage(self):
        BrickMypageLocation.objects.create(
            brick_id=bricks.OpenStreetMapFilteredMapBrick.id, order=20, user=None,
        )

    def _populate_bricks_config_for_root(self):
        # Add this block only if the root user exists (creme_core populated)
        root = get_user_model().objects.filter(pk=1).first()
        if root:
            logger.info(
                'The block OpenStreetMapFilteredMapBrick is set on the page of "root" user.'
            )
            BrickMypageLocation.objects.create(
                brick_id=bricks.OpenStreetMapFilteredMapBrick.id, order=20, user=root,
            )

    def _populate_bricks_config(self):
        self._populate_bricks_config_for_persons()
        self._populate_bricks_config_for_mypage()
        self._populate_bricks_config_for_root()
