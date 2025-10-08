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
from django.utils.translation import pgettext

import creme.creme_core.bricks as core_bricks
from creme import persons
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.gui.menu import ContainerEntry
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (
    BrickDetailviewLocation,
    ButtonMenuItem,
    FieldsConfig,
    HeaderFilter,
    MenuConfigItem,
    RelationBrickItem,
    RelationType,
    SearchConfigItem,
)

from . import (
    buttons,
    constants,
    custom_forms,
    get_ticket_model,
    get_tickettemplate_model,
)
from .menu import TicketsEntry
from .models import Criticity, Priority, Status

logger = logging.getLogger(__name__)

Ticket = get_ticket_model()
TicketTemplate = get_tickettemplate_model()

# UUIDs for instances which can be deleted
UUID_PRIORITY_LOW      = '87599d36-8133-41b7-a382-399d5e96b160'
UUID_PRIORITY_NORMAL   = '816cefa7-2f30-46a6-8baa-92e4647f44d3'
UUID_PRIORITY_HIGH     = '42c39215-cf78-4d0b-b00b-b54a6680f71a'
UUID_PRIORITY_URGENT   = '69bdbe35-cf99-4168-abb3-389aab6b7313'
UUID_PRIORITY_BLOCKING = 'd2dba4cb-382c-4d94-8306-4ec739f03144'

UUID_CRITICALITY_MINOR       = '368a6b62-c66e-4286-b841-1062f59133c9'
UUID_CRITICALITY_MAJOR       = '1aa05ca4-68ec-4068-ac3b-b9ddffaeb0aa'
UUID_CRITICALITY_FEATURE     = 'e5a2a80e-36e8-49fd-8b2b-e802ccd4090c'
UUID_CRITICALITY_CRITICAL    = '9937c865-d0e7-4f33-92f3-600814e293ad'
UUID_CRITICALITY_ENHANCEMENT = '8e509e5e-8bd6-4cd0-8f96-5c129f0a875d'
UUID_CRITICALITY_ERROR       = '3bd07632-f3ad-415e-bb33-95c723e46aa5'


class Populator(BasePopulator):
    dependencies = ['creme_core', 'activities']

    RELATION_TYPES = [
        RelationType.objects.builder(
            id=constants.REL_SUB_LINKED_2_TICKET,
            predicate=_('is linked to the ticket'),
        ).symmetric(
            id=constants.REL_OBJ_LINKED_2_TICKET,
            predicate=_('(ticket) linked to the entity'),
            models=[Ticket],
        ),
    ]
    HEADER_FILTERS = [
        HeaderFilter.objects.proxy(
            id=constants.DEFAULT_HFILTER_TICKET,
            model=Ticket,
            name=_('Ticket view'),
            cells=[
                (EntityCellRegularField, 'number'),
                (EntityCellRegularField, 'title'),
                (EntityCellRegularField, 'status'),
                (EntityCellRegularField, 'priority'),
                (EntityCellRegularField, 'criticity'),
                (EntityCellRegularField, 'closing_date'),
            ],
        ),
        HeaderFilter.objects.proxy(
            id=constants.DEFAULT_HFILTER_TTEMPLATE,
            model=TicketTemplate,
            name=_('Ticket template view'),
            cells=[
                (EntityCellRegularField, 'title'),
                (EntityCellRegularField, 'status'),
                (EntityCellRegularField, 'priority'),
                (EntityCellRegularField, 'criticity'),
            ],
        ),
    ]
    CUSTOM_FORMS = [
        custom_forms.TICKET_CREATION_CFORM,
        custom_forms.TICKET_EDITION_CFORM,
        custom_forms.TTEMPLATE_CREATION_CFORM,
        custom_forms.TTEMPLATE_EDITION_CFORM,
    ]
    BUTTONS = [
        ButtonMenuItem.objects.proxy(
            model=persons.get_contact_model(), button=buttons.Linked2TicketButton, order=1050,
        ),

        ButtonMenuItem.objects.proxy(
            model=persons.get_organisation_model(), button=buttons.Linked2TicketButton, order=1050,
        )
    ]
    # SEARCH = [
    #     'title', 'number', 'description',
    #     'status__name', 'priority__name', 'criticity__name',
    # ]
    SEARCH = [
        SearchConfigItem.objects.builder(
            model=Ticket,
            fields=[
                'title', 'number', 'description',
                'status__name', 'priority__name', 'criticity__name',
            ],
        ),
    ]
    STATUSES = [
        Status(
            uuid=constants.UUID_STATUS_OPEN,
            name=pgettext('tickets-status', 'Open'),
            is_closed=False, color='f8f223', is_custom=False, order=1,
        ),
        Status(
            uuid=constants.UUID_STATUS_CLOSED,
            name=pgettext('tickets-status', 'Closed'),
            is_closed=True, color='1dd420', is_custom=False, order=2,
        ),
        Status(
            uuid=constants.UUID_STATUS_INVALID,
            name=pgettext('tickets-status', 'Invalid'),
            is_closed=False, color='adadad', is_custom=False, order=3,
        ),
        Status(
            uuid=constants.UUID_STATUS_DUPLICATED,
            name=pgettext('tickets-status', 'Duplicated'),
            is_closed=False, color='ababab', is_custom=False, order=4,
        ),
        Status(
            uuid=constants.UUID_STATUS_WONT_FIX,
            name=_("Won't fix"),
            is_closed=False, color='a387ab', is_custom=False, order=5,
        ),
    ]
    PRIORITIES = [
        # is_custom=True => only created during the first execution
        Priority(uuid=UUID_PRIORITY_LOW,      name=_('Low'),      order=1),
        Priority(uuid=UUID_PRIORITY_NORMAL,   name=_('Normal'),   order=2),
        Priority(uuid=UUID_PRIORITY_HIGH,     name=_('High'),     order=3),
        Priority(uuid=UUID_PRIORITY_URGENT,   name=_('Urgent'),   order=4),
        Priority(uuid=UUID_PRIORITY_BLOCKING, name=_('Blocking'), order=5),
    ]
    CRITICALITY = [
        # is_custom=True => only created during the first execution
        Criticity(uuid=UUID_CRITICALITY_MINOR,       name=_('Minor'),       order=1),
        Criticity(uuid=UUID_CRITICALITY_MAJOR,       name=_('Major'),       order=2),
        Criticity(uuid=UUID_CRITICALITY_FEATURE,     name=_('Feature'),     order=3),
        Criticity(uuid=UUID_CRITICALITY_CRITICAL,    name=_('Critical'),    order=4),
        Criticity(uuid=UUID_CRITICALITY_ENHANCEMENT, name=_('Enhancement'), order=5),
        Criticity(uuid=UUID_CRITICALITY_ERROR,       name=_('Error'),       order=6),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.Ticket = get_ticket_model()
        # self.TicketTemplate = get_tickettemplate_model()
        self.Ticket         = Ticket
        self.TicketTemplate = TicketTemplate

    def _already_populated(self):
        return RelationType.objects.filter(
            pk=constants.REL_SUB_LINKED_2_TICKET,
        ).exists()

    def _populate(self):
        super()._populate()
        self._populate_statuses()
        self._populate_priorities()
        self._populate_criticality()

    def _first_populate(self):
        super()._first_populate()
        self._populate_fields_config()

    def _populate_statuses(self):
        self._save_minions(self.STATUSES)

    def _populate_fields_config(self):
        for model in (self.Ticket, self.TicketTemplate):
            FieldsConfig.objects.create(
                content_type=model,
                descriptions=[('description', {FieldsConfig.REQUIRED: True})],
            )

    def _populate_priorities(self):
        self._save_minions(self.PRIORITIES)

    def _populate_criticality(self):
        self._save_minions(self.CRITICALITY)

    def _populate_relation_types(self):
        # RelationType.objects.smart_update_or_create(
        #     (
        #         constants.REL_SUB_LINKED_2_TICKET,
        #         _('is linked to the ticket'),
        #     ),
        #     (
        #         constants.REL_OBJ_LINKED_2_TICKET,
        #         _('(ticket) linked to the entity'),
        #         [self.Ticket],
        #     ),
        # )
        super()._populate_relation_types()

        if apps.is_installed('creme.activities'):
            logger.info(
                'Activities app is installed => a Ticket can be the subject of an Activity'
            )

            from creme.activities.constants import REL_SUB_ACTIVITY_SUBJECT

            RelationType.objects.get(
                pk=REL_SUB_ACTIVITY_SUBJECT,
            ).add_subject_ctypes(self.Ticket)

    # def _populate_header_filters(self):
    #     create_hf = HeaderFilter.objects.create_if_needed
    #     create_hf(
    #         pk=constants.DEFAULT_HFILTER_TICKET,
    #         model=self.Ticket,
    #         name=_('Ticket view'),
    #         cells_desc=[
    #             (EntityCellRegularField, {'name': 'number'}),
    #             (EntityCellRegularField, {'name': 'title'}),
    #             (EntityCellRegularField, {'name': 'status'}),
    #             (EntityCellRegularField, {'name': 'priority'}),
    #             (EntityCellRegularField, {'name': 'criticity'}),
    #             (EntityCellRegularField, {'name': 'closing_date'}),
    #         ],
    #     )
    #     create_hf(
    #         pk=constants.DEFAULT_HFILTER_TTEMPLATE,
    #         model=self.TicketTemplate,
    #         name=_('Ticket template view'),
    #         cells_desc=[
    #             (EntityCellRegularField, {'name': 'title'}),
    #             (EntityCellRegularField, {'name': 'status'}),
    #             (EntityCellRegularField, {'name': 'priority'}),
    #             (EntityCellRegularField, {'name': 'criticity'}),
    #         ],
    #     )

    # def _populate_search_config(self):
    #     SearchConfigItem.objects.create_if_needed(
    #         model=self.Ticket, fields=self.SEARCH,
    #     )

    def _populate_menu_config(self):
        menu_container = MenuConfigItem.objects.get_or_create(
            entry_id=ContainerEntry.id,
            entry_data={'label': _('Tools')},
            role=None, superuser=False,
            defaults={'order': 100},
        )[0]

        MenuConfigItem.objects.create(
            entry_id=TicketsEntry.id, parent=menu_container, order=100,
        )

    # def _populate_buttons_config(self):
    #     if apps.is_installed('creme.persons'):
    #         from creme import persons
    #         from creme.tickets.buttons import Linked2TicketButton
    #
    #         create_bmi = ButtonMenuItem.objects.create_if_needed
    #         for model in (persons.get_contact_model(), persons.get_organisation_model()):
    #             create_bmi(model=model, button=Linked2TicketButton, order=1050)

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
