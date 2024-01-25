################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2024  Hybird
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
    ButtonMenuItem,
    CustomFormConfigItem,
    FieldsConfig,
    HeaderFilter,
    MenuConfigItem,
    RelationBrickItem,
    RelationType,
    SearchConfigItem,
)
from creme.creme_core.utils import create_if_needed

from . import (
    constants,
    custom_forms,
    get_ticket_model,
    get_tickettemplate_model,
)
from .menu import TicketsEntry
from .models import Criticity, Priority, Status
from .models.status import BASE_STATUS

logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core', 'activities']

    SEARCH = [
        'title', 'number', 'description',
        'status__name', 'priority__name', 'criticity__name',
    ]
    PRIORITIES = [_('Low'), _('Normal'), _('High'), _('Urgent'), _('Blocking')]
    CRITICALITY = [
        _('Minor'), _('Major'), _('Feature'), _('Critical'), _('Enhancement'), _('Error'),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.Ticket = get_ticket_model()
        self.TicketTemplate = get_tickettemplate_model()

    def _already_populated(self):
        return RelationType.objects.filter(
            pk=constants.REL_SUB_LINKED_2_TICKET,
        ).exists()

    def _populate(self):
        super()._populate()
        self._populate_statuses()

    def _first_populate(self):
        super()._first_populate()
        self._populate_fields_config()
        self._populate_priorities()
        self._populate_criticality()

    def _populate_statuses(self):
        for pk, name, is_closed, color in BASE_STATUS:
            create_if_needed(
                Status,
                {'pk': pk},
                name=str(name),
                is_closed=is_closed,
                color=color,
                is_custom=False,
                order=pk,
            )

    def _populate_fields_config(self):
        for model in (self.Ticket, self.TicketTemplate):
            FieldsConfig.objects.create(
                content_type=model,
                descriptions=[('description', {FieldsConfig.REQUIRED: True})],
            )

    def _populate_priorities(self):
        for i, name in enumerate(self.PRIORITIES, start=1):
            create_if_needed(Priority, {'pk': i}, name=name, order=i)

    def _populate_criticality(self):
        for i, name in enumerate(self.CRITICALITY, start=1):
            create_if_needed(Criticity, {'pk': i}, name=name, order=i)

    def _populate_relation_types(self):
        RelationType.objects.smart_update_or_create(
            (
                constants.REL_SUB_LINKED_2_TICKET,
                _('is linked to the ticket'),
            ),
            (
                constants.REL_OBJ_LINKED_2_TICKET,
                _('(ticket) linked to the entity'),
                [self.Ticket],
            ),
        )

        if apps.is_installed('creme.activities'):
            logger.info(
                'Activities app is installed => a Ticket can be the subject of an Activity'
            )

            from creme.activities.constants import REL_SUB_ACTIVITY_SUBJECT

            RelationType.objects.get(
                pk=REL_SUB_ACTIVITY_SUBJECT,
            ).add_subject_ctypes(self.Ticket)

    def _populate_header_filters(self):
        create_hf = HeaderFilter.objects.create_if_needed
        create_hf(
            pk=constants.DEFAULT_HFILTER_TICKET,
            model=self.Ticket,
            name=_('Ticket view'),
            cells_desc=[
                (EntityCellRegularField, {'name': 'number'}),
                (EntityCellRegularField, {'name': 'title'}),
                (EntityCellRegularField, {'name': 'status'}),
                (EntityCellRegularField, {'name': 'priority'}),
                (EntityCellRegularField, {'name': 'criticity'}),
                (EntityCellRegularField, {'name': 'closing_date'}),
            ],
        )
        create_hf(
            pk=constants.DEFAULT_HFILTER_TTEMPLATE,
            model=self.TicketTemplate,
            name=_('Ticket template view'),
            cells_desc=[
                (EntityCellRegularField, {'name': 'title'}),
                (EntityCellRegularField, {'name': 'status'}),
                (EntityCellRegularField, {'name': 'priority'}),
                (EntityCellRegularField, {'name': 'criticity'}),
            ],
        )

    def _populate_custom_forms(self):
        create_cfci = CustomFormConfigItem.objects.create_if_needed
        create_cfci(descriptor=custom_forms.TICKET_CREATION_CFORM)
        create_cfci(descriptor=custom_forms.TICKET_EDITION_CFORM)
        create_cfci(descriptor=custom_forms.TTEMPLATE_CREATION_CFORM)
        create_cfci(descriptor=custom_forms.TTEMPLATE_EDITION_CFORM)

    def _populate_search_config(self):
        SearchConfigItem.objects.create_if_needed(
            model=self.Ticket, fields=self.SEARCH,
        )

    def _populate_menu_config(self):
        menu_container = MenuConfigItem.objects.get_or_create(
            entry_id=ContainerEntry.id,
            entry_data={'label': _('Tools')},
            defaults={'order': 100},
        )[0]

        MenuConfigItem.objects.create(
            entry_id=TicketsEntry.id, parent=menu_container, order=100,
        )

    def _populate_buttons_config(self):
        if apps.is_installed('creme.persons'):
            from creme import persons
            from creme.tickets.buttons import Linked2TicketButton

            create_bmi = ButtonMenuItem.objects.create_if_needed
            for model in (persons.get_contact_model(), persons.get_organisation_model()):
                create_bmi(model=model, button=Linked2TicketButton, order=50)

    def _populate_bricks_config(self):
        Ticket = self.Ticket
        rbi = RelationBrickItem.objects.get_or_create(
            relation_type_id=constants.REL_OBJ_LINKED_2_TICKET,
        )[0]

        RIGHT = BrickDetailviewLocation.RIGHT

        BrickDetailviewLocation.objects.multi_create(
            defaults={'model': Ticket, 'zone': BrickDetailviewLocation.LEFT},
            data=[
                {'order': 5},
                {'brick': core_bricks.CustomFieldsBrick, 'order':  40},
                {'brick': core_bricks.PropertiesBrick,   'order': 450},
                {'brick': core_bricks.RelationsBrick,    'order': 500},

                {'brick': rbi.brick_id,             'order':  1, 'zone': RIGHT},
                {'brick': core_bricks.HistoryBrick, 'order': 20, 'zone': RIGHT},
            ]
        )

        if apps.is_installed('creme.assistants'):
            logger.info(
                'Assistants app is installed => we use the assistants blocks on detail view'
            )

            import creme.assistants.bricks as a_bricks

            BrickDetailviewLocation.objects.multi_create(
                defaults={'model': Ticket, 'zone': RIGHT},
                data=[
                    {'brick': a_bricks.TodosBrick,        'order': 100},
                    {'brick': a_bricks.MemosBrick,        'order': 200},
                    {'brick': a_bricks.AlertsBrick,       'order': 300},
                    {'brick': a_bricks.UserMessagesBrick, 'order': 400},
                ],
            )

        if apps.is_installed('creme.documents'):
            # logger.info("Documents app is installed
            # => we use the documents block on Ticket's detail views")

            from creme.documents.bricks import LinkedDocsBrick

            BrickDetailviewLocation.objects.create_if_needed(
                brick=LinkedDocsBrick, order=600, zone=RIGHT, model=Ticket,
            )
