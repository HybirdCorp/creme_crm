# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014-2018  Hybird
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

from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import BrickDetailviewLocation, BrickMypageLocation, SettingValue

from creme import persons

from . import bricks, constants, setting_keys
from .management.commands.geolocation import Command as GeolocationCommand


logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core', 'persons']

    def populate(self):
        already_populated = SettingValue.objects.filter(key_id=setting_keys.NEIGHBOURHOOD_DISTANCE.id).exists()

        create_skey = SettingValue.objects.get_or_create
        create_skey(key_id=setting_keys.NEIGHBOURHOOD_DISTANCE.id, defaults={'value': constants.DEFAULT_SEPARATING_NEIGHBOURS})
        create_skey(key_id=setting_keys.GOOGLE_API_KEY.id,         defaults={'value': ''})

        if not already_populated:
            if self.verbosity:
                self.stdout.write('\n ', ending='')
                self.stdout.flush()

            GeolocationCommand().import_town_all(verbosity=self.verbosity)

        if not already_populated:
            Contact      = persons.get_contact_model()
            Organisation = persons.get_organisation_model()

            create_bdl = BrickDetailviewLocation.create_if_needed
            create_bdl(brick_id=bricks.GoogleDetailMapBrick.id_, order=70, zone=BrickDetailviewLocation.LEFT, model=Organisation)
            create_bdl(brick_id=bricks.GoogleDetailMapBrick.id_, order=70, zone=BrickDetailviewLocation.LEFT, model=Contact)
            create_bdl(brick_id=bricks.GoogleNeighboursMapBrick.id_, order=600, zone=BrickDetailviewLocation.BOTTOM, model=Organisation)
            create_bdl(brick_id=bricks.GoogleNeighboursMapBrick.id_, order=600, zone=BrickDetailviewLocation.BOTTOM, model=Contact)

            BrickMypageLocation.objects.create(brick_id=bricks.GoogleFilteredMapBrick.id_, order=20, user=None)

            # Add this bloc only if the root user exists (creme_core populated)
            root = get_user_model().objects.filter(pk=1).first()
            if root:
                logger.info('Creme core is installed => the block PersonsFilterMap can be activated')
                BrickMypageLocation.objects.create(brick_id=bricks.GoogleFilteredMapBrick.id_, order=8, user=root)
