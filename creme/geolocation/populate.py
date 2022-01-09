# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014-2022  Hybird
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

    def populate(self):
        already_populated = SettingValue.objects.exists_4_key(setting_keys.NEIGHBOURHOOD_DISTANCE)

        if already_populated:
            return

        SettingValue.objects.set_4_key(
            setting_keys.NEIGHBOURHOOD_DISTANCE,
            constants.DEFAULT_SEPARATING_NEIGHBOURS
        )

        SettingValue.objects.set_4_key(setting_keys.GOOGLE_API_KEY, '')

        if self.verbosity:
            self.stdout.write('\n ', ending='')
            self.stdout.flush()

        GeolocationCommand().import_town_all(verbosity=self.verbosity)

        for model in (persons.get_organisation_model(), persons.get_contact_model()):
            BrickDetailviewLocation.objects.multi_create(
                defaults={'model': model},
                data=[
                    {
                        'brick': bricks.GoogleDetailMapBrick, 'order': 70,
                        'zone': BrickDetailviewLocation.LEFT,
                    },
                    {
                        'brick': bricks.GoogleNeighboursMapBrick, 'order': 600,
                        'zone': BrickDetailviewLocation.BOTTOM,
                    },
                ],
            )

        BrickMypageLocation.objects.create(
            brick_id=bricks.GoogleFilteredMapBrick.id_, order=20, user=None,
        )

        # Add this block only if the root user exists (creme_core populated)
        root = get_user_model().objects.filter(pk=1).first()
        if root:
            logger.info(
                'Creme core is installed => the block GoogleFilteredMapBrick can be activated'
            )
            BrickMypageLocation.objects.create(
                brick_id=bricks.GoogleFilteredMapBrick.id_, order=20, user=root,
            )
