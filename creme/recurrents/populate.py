################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2023  Hybird
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

from django.conf import settings
from django.utils.translation import gettext as _

from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.gui.menu import ContainerEntry
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (
    CustomFormConfigItem,
    HeaderFilter,
    Job,
    MenuConfigItem,
    SearchConfigItem,
)

from . import constants, custom_forms, get_rgenerator_model
from .creme_jobs import recurrents_gendocs_type
from .menu import RecurrentGeneratorsEntry


class Populator(BasePopulator):
    dependencies = ['creme_core']

    def populate(self):
        RecurrentGenerator = get_rgenerator_model()

        _job, job_created = Job.objects.get_or_create(
            type_id=recurrents_gendocs_type.id,
            defaults={
                'language': settings.LANGUAGE_CODE,
                'status':   Job.STATUS_OK,
            },
        )

        already_populated = not job_created

        # ---------------------------
        HeaderFilter.objects.create_if_needed(
            pk=constants.DEFAULT_HFILTER_RGENERATOR,
            model=RecurrentGenerator,
            name=_('Generator view'),
            cells_desc=[(EntityCellRegularField, {'name': 'name'})],
        )

        # ---------------------------
        CustomFormConfigItem.objects.create_if_needed(
            descriptor=custom_forms.GENERATOR_CREATION_CFORM,
        )
        CustomFormConfigItem.objects.create_if_needed(
            descriptor=custom_forms.GENERATOR_EDITION_CFORM,
        )

        # ---------------------------
        SearchConfigItem.objects.create_if_needed(RecurrentGenerator, ['name', 'description'])

        # ---------------------------
        if not already_populated:
            container = MenuConfigItem.objects.get_or_create(
                entry_id=ContainerEntry.id,
                entry_data={'label': _('Management')},
                defaults={'order': 50},
            )[0]
            MenuConfigItem.objects.create(
                entry_id=RecurrentGeneratorsEntry.id, parent=container,  order=100,
            )
