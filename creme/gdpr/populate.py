################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2023  Hybird
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

from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import CremePropertyType, Job
from creme.creme_core.utils.date_period import date_period_registry

from . import constants
from .creme_jobs import anonymiser_type


class Populator(BasePopulator):
    # dependencies = ['creme_core']

    def populate(self):
        CremePropertyType.objects.smart_update_or_create(
            str_pk=constants.PROP_IS_ANONYMIZED,
            text=_('is anonymized'),
        )

        # ---------------------------
        Job.objects.get_or_create(
            type_id=anonymiser_type.id,
            defaults={
                'language': settings.LANGUAGE_CODE,
                'periodicity': date_period_registry.get_period('days', 1),  # TODO: more?
                'status': Job.STATUS_OK,
                'enabled': False,
            },
        )

        # # ---------------------------
        # if not not already_populated:
        #     container = MenuConfigItem.objects.get_or_create(
        #         entry_id=ContainerEntry.id,
        #         entry_data={'label': _('Management')},
        #         defaults={'order': 50},
        #     )[0]
        #
        #     MenuConfigItem.objects.create(
        #         entry_id=RecurrentGeneratorsEntry.id, parent=container,  order=100,
        #     )
