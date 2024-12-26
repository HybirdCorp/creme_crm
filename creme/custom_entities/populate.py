################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024  Hybird
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
from creme.creme_core.models import CustomFormConfigItem

from . import custom_forms

logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core']

    def _already_populated(self):
        return False

    def _populate_custom_forms(self):
        create_cfci = CustomFormConfigItem.objects.create_if_needed

        for descriptor in custom_forms.creation_descriptors.values():
            create_cfci(descriptor=descriptor)

        for descriptor in custom_forms.edition_descriptors.values():
            create_cfci(descriptor=descriptor)
