################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2021-2023  Hybird
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

from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import MenuConfigItem

from .menu import CremeConfigEntry


class Populator(BasePopulator):
    def populate(self):
        MenuConfigItem.objects.get_or_create(
            entry_id=CremeConfigEntry.id,
            role=None,
            superuser=False,
            defaults={'order': 990},
        )
