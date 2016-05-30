# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014-2016  Hybird
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
from creme.creme_core.models import BlockDetailviewLocation, BlockMypageLocation, SettingValue

from creme.persons import get_contact_model, get_organisation_model

from .blocks import persons_maps_block, persons_filter_maps_block, who_is_around_maps_block
from .constants import DEFAULT_SEPARATING_NEIGHBOURS
from .management.commands.geolocation import Command as GeolocationCommand
from .setting_keys import NEIGHBOURHOOD_DISTANCE

logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core', 'persons']

    def populate(self):
        already_populated = SettingValue.objects.filter(key_id=NEIGHBOURHOOD_DISTANCE.id).exists()

        # SettingValue.create_if_needed(key=NEIGHBOURHOOD_DISTANCE, user=None, value=DEFAULT_SEPARATING_NEIGHBOURS)
        SettingValue.objects.get_or_create(key_id=NEIGHBOURHOOD_DISTANCE.id,
                                           defaults={'value': DEFAULT_SEPARATING_NEIGHBOURS},
                                          )

        if not already_populated:
            if self.verbosity:
                self.stdout.write('\n ', ending='')
                self.stdout.flush()

            GeolocationCommand().import_town_all(verbosity=self.verbosity)

        if not already_populated:
            Contact = get_contact_model()
            Organisation = get_organisation_model()

            create_bdl = BlockDetailviewLocation.create
            create_bdl(block_id=persons_maps_block.id_, order=70, zone=BlockDetailviewLocation.LEFT, model=Organisation)
            create_bdl(block_id=persons_maps_block.id_, order=70, zone=BlockDetailviewLocation.LEFT, model=Contact)
            create_bdl(block_id=who_is_around_maps_block.id_, order=600, zone=BlockDetailviewLocation.BOTTOM, model=Organisation)
            create_bdl(block_id=who_is_around_maps_block.id_, order=600, zone=BlockDetailviewLocation.BOTTOM, model=Contact)

            BlockMypageLocation.create(block_id=persons_filter_maps_block.id_, order=20)

            # Add this bloc only if the root user exists (creme_core populated)
            root = get_user_model().objects.filter(pk=1).first()
            if root:
                logger.info('Creme core is installed => the block PersonsFilterMap can be activated')
                BlockMypageLocation.create(block_id=persons_filter_maps_block.id_, order=8, user=root)
