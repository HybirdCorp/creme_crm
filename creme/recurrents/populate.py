# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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
from creme.creme_core.gui.custom_form import EntityCellCustomFormSpecial
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (
    CustomFormConfigItem,
    HeaderFilter,
    Job,
    SearchConfigItem,
)

from . import constants, custom_forms, get_rgenerator_model
from .creme_jobs import recurrents_gendocs_type
from .forms.recurrentgenerator import GeneratorCTypeSubCell


class Populator(BasePopulator):
    dependencies = ['creme_core']

    def populate(self):
        RecurrentGenerator = get_rgenerator_model()

        HeaderFilter.objects.create_if_needed(
            pk=constants.DEFAULT_HFILTER_RGENERATOR,
            model=RecurrentGenerator,
            name=_('Generator view'),
            cells_desc=[(EntityCellRegularField, {'name': 'name'})],
        )

        # ---------------------------
        common_groups_desc = [
            {
                'name': _('Description'),
                'cells': [
                    (EntityCellRegularField, {'name': 'description'}),
                ],
            }, {
                'name': _('Custom fields'),
                'cells': [
                    (
                        EntityCellCustomFormSpecial,
                        {'name': EntityCellCustomFormSpecial.REMAINING_CUSTOMFIELDS},
                    ),
                ],
            }
        ]

        CustomFormConfigItem.objects.create_if_needed(
            descriptor=custom_forms.GENERATOR_CREATION_CFORM,
            groups_desc=[
                {
                    'name': _('General information'),
                    'cells': [
                        (EntityCellRegularField, {'name': 'user'}),
                        (EntityCellRegularField, {'name': 'name'}),
                        GeneratorCTypeSubCell(model=RecurrentGenerator).into_cell(),
                        (EntityCellRegularField, {'name': 'first_generation'}),
                        (EntityCellRegularField, {'name': 'periodicity'}),
                        (
                            EntityCellCustomFormSpecial,
                            {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                        ),
                    ],
                },
                *common_groups_desc,
                {
                    'name': _('Properties'),
                    'cells': [
                        (
                            EntityCellCustomFormSpecial,
                            {'name': EntityCellCustomFormSpecial.CREME_PROPERTIES},
                        ),
                    ],
                }, {
                    'name': _('Relationships'),
                    'cells': [
                        (
                            EntityCellCustomFormSpecial,
                            {'name': EntityCellCustomFormSpecial.RELATIONS},
                        ),
                    ],
                },
            ],
        )
        CustomFormConfigItem.objects.create_if_needed(
            descriptor=custom_forms.GENERATOR_EDITION_CFORM,
            groups_desc=[
                {
                    'name': _('General information'),
                    'cells': [
                        (EntityCellRegularField, {'name': 'user'}),
                        (EntityCellRegularField, {'name': 'name'}),
                        (EntityCellRegularField, {'name': 'first_generation'}),
                        (EntityCellRegularField, {'name': 'periodicity'}),
                        (
                            EntityCellCustomFormSpecial,
                            {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                        ),
                    ],
                },
                *common_groups_desc,
            ],
        )

        # ---------------------------
        SearchConfigItem.objects.create_if_needed(RecurrentGenerator, ['name', 'description'])

        # ---------------------------
        Job.objects.get_or_create(
            type_id=recurrents_gendocs_type.id,
            defaults={
                'language': settings.LANGUAGE_CODE,
                'status':   Job.STATUS_OK,
            },
        )
