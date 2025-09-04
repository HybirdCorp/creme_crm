################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2020-2025  Hybird
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

from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import SettingValue

from . import setting_keys

logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core', 'persons']

    SETTING_VALUES = [
        SettingValue(
            key=setting_keys.location_map_url_key,
            value='https://www.google.com/maps/?q={search}',
        ),
    ]

    # def populate(self):
    #     already_populated = SettingValue.objects.exists_4_key(setting_keys.location_map_url_key)
    #
    #     if not already_populated:
    #         SettingValue.objects.set_4_key(
    #             setting_keys.location_map_url_key,
    #             'https://www.google.com/maps/?q={search}'
    #         )
    def _already_populated(self):
        return SettingValue.objects.exists_4_key(setting_keys.location_map_url_key)
