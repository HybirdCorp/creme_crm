################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2021  Hybird
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

from django.utils.translation import gettext as _

from creme.creme_core.gui.menu import ContainerEntry
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import MenuConfigItem

from .menu import VFCsImportEntry


class Populator(BasePopulator):
    def populate(self):
        # TODO: need a reliable way to know if already populated...
        if not MenuConfigItem.objects.filter(entry_id__startswith='vcfs-').exists():
            directory = MenuConfigItem.objects.filter(
                entry_id=ContainerEntry.id,
                entry_data={'label': _('Directory')},
            ).first()

            if directory is not None:
                MenuConfigItem.objects.create(
                    entry_id=VFCsImportEntry.id,
                    parent=directory,
                    order=200,
                )
