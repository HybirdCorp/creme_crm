################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from django.apps import apps
from django.utils.translation import gettext as _

import creme.creme_core.bricks as core_bricks
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.gui.menu import ContainerEntry
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (
    BrickDetailviewLocation,
    HeaderFilter,
    MenuConfigItem,
    SearchConfigItem,
)

from . import bricks, constants, custom_forms, get_report_model
from .menu import ReportsEntry

logger = logging.getLogger(__name__)

Report = get_report_model()


class Populator(BasePopulator):
    dependencies = ['creme_core']

    HEADER_FILTERS = [
        HeaderFilter.objects.proxy(
            id=constants.DEFAULT_HFILTER_REPORT,
            name=_('Report view'),
            model=Report,
            cells=[
                (EntityCellRegularField, 'name'),
                (EntityCellRegularField, 'ct'),
            ],
        ),
    ]
    CUSTOM_FORMS = [
        custom_forms.REPORT_CREATION_CFORM,
        custom_forms.REPORT_EDITION_CFORM,
    ]
    # SEARCH = ['name']
    SEARCH = [
        SearchConfigItem.objects.builder(model=Report, fields=['name']),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.Report = get_report_model()
        self.Report = Report

    def _already_populated(self):
        return HeaderFilter.objects.filter(id=constants.DEFAULT_HFILTER_REPORT).exists()

    # def _populate_header_filters(self):
    #     HeaderFilter.objects.create_if_needed(
    #         pk=constants.DEFAULT_HFILTER_REPORT,
    #         name=_('Report view'), model=self.Report,
    #         cells_desc=[
    #             (EntityCellRegularField, {'name': 'name'}),
    #             (EntityCellRegularField, {'name': 'ct'}),
    #         ],
    #     )

    # def _populate_search_config(self):
    #     SearchConfigItem.objects.create_if_needed(model=self.Report, fields=self.SEARCH)

    def _populate_menu_config(self):
        menu_container = MenuConfigItem.objects.get_or_create(
            entry_id=ContainerEntry.id,
            entry_data={'label': _('Analysis')},
            role=None, superuser=False,
            defaults={'order': 500},
        )[0]

        MenuConfigItem.objects.create(
            entry_id=ReportsEntry.id, parent=menu_container, order=20,
        )

    def _populate_bricks_config(self):
        RIGHT = BrickDetailviewLocation.RIGHT

        BrickDetailviewLocation.objects.multi_create(
            defaults={'model': self.Report, 'zone': BrickDetailviewLocation.LEFT},
            data=[
                {'order': 5},
                {'brick': core_bricks.CustomFieldsBrick,    'order':  40},
                {'brick': bricks.ReportFieldsBrick,         'order':  50},
                # {'brick': bricks.ReportGraphChartListBrick, 'order':  60},
                {'brick': bricks.ReportChartsBrick,         'order':  60},
                {'brick': core_bricks.PropertiesBrick,      'order': 450},
                {'brick': core_bricks.RelationsBrick,       'order': 500},

                {'brick': core_bricks.HistoryBrick, 'order': 20, 'zone': RIGHT},
            ],
        )

        if apps.is_installed('creme.assistants'):
            logger.info(
                'Assistants app is installed'
                ' => we use the assistants blocks on detail view'
            )

            import creme.assistants.bricks as a_bricks

            BrickDetailviewLocation.objects.multi_create(
                defaults={'model': self.Report, 'zone': RIGHT},
                data=[
                    {'brick': a_bricks.TodosBrick,        'order': 100},
                    {'brick': a_bricks.MemosBrick,        'order': 200},
                    {'brick': a_bricks.AlertsBrick,       'order': 300},
                    {'brick': a_bricks.UserMessagesBrick, 'order': 400},
                ],
            )

        if apps.is_installed('creme.documents'):
            # logger.info('Documents app is installed
            # => we use the documents block on detail views')

            from creme.documents.bricks import LinkedDocsBrick

            BrickDetailviewLocation.objects.create_if_needed(
                brick=LinkedDocsBrick, order=600, zone=RIGHT, model=self.Report,
            )
