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
# from creme.creme_core.models import CustomFormConfigItem
from creme.creme_core.models import (
    BrickDetailviewLocation,
    HeaderFilter,
    MenuConfigItem,
    RelationType,
    SearchConfigItem,
)
from creme.opportunities import get_opportunity_model
from creme.persons import get_contact_model

from . import bricks, constants, custom_forms, get_event_model
from .menu import EventsEntry
from .models import EventType

logger = logging.getLogger(__name__)

# UUIDs for instances which can be deleted
UUID_EVENT_TYPE_SHOW       = 'd4928cbc-6afd-40bf-9d07-815b8b920b39'
UUID_EVENT_TYPE_CONFERENCE = '254fda4f-1a01-47e1-b5aa-a1b2d4ef2890'
UUID_EVENT_TYPE_BREAKFAST  = 'b520fe79-98f4-4362-8293-b4febd46c9df'
UUID_EVENT_TYPE_BRUNCH     = '42c72e13-9f47-4ea8-bd9b-0a0764ceea19'


class Populator(BasePopulator):
    dependencies = ['creme_core']

    CUSTOM_FORMS = [
        custom_forms.EVENT_CREATION_CFORM,
        custom_forms.EVENT_EDITION_CFORM,
    ]
    SEARCH = ['name', 'description', 'type__name']
    EVENT_TYPES = [
        # is_custom=True => only created during the first execution
        EventType(uuid=UUID_EVENT_TYPE_SHOW,       name=_('Show')),
        EventType(uuid=UUID_EVENT_TYPE_CONFERENCE, name=_('Conference')),
        EventType(uuid=UUID_EVENT_TYPE_BREAKFAST,  name=_('Breakfast')),
        EventType(uuid=UUID_EVENT_TYPE_BRUNCH,     name=_('Brunch')),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.Event = get_event_model()
        self.Contact = get_contact_model()
        self.Opportunity = get_opportunity_model()

    def _already_populated(self):
        return RelationType.objects.filter(
            pk=constants.REL_SUB_IS_INVITED_TO,
        ).exists()

    def _populate(self):
        super()._populate()
        self._populate_event_types()

    def _populate_event_types(self):
        self._save_minions(self.EVENT_TYPES)

    def _populate_relation_types(self):
        Event = self.Event
        Contact = self.Contact

        create_rtype = RelationType.objects.smart_update_or_create
        create_rtype(
            (constants.REL_SUB_IS_INVITED_TO, _('is invited to the event'), [Contact]),
            (constants.REL_OBJ_IS_INVITED_TO, _('has invited'),             [Event]),
            is_internal=True,
        )
        create_rtype(
            (
                constants.REL_SUB_ACCEPTED_INVITATION,
                _('accepted the invitation to the event'),
                [Contact],
            ), (
                constants.REL_OBJ_ACCEPTED_INVITATION,
                _('prepares to receive'),
                [Event],
            ),
            is_internal=True,
        )
        create_rtype(
            (
                constants.REL_SUB_REFUSED_INVITATION,
                _('refused the invitation to the event'),
                [Contact],
            ), (
                constants.REL_OBJ_REFUSED_INVITATION,
                _('do not prepare to receive any more'),
                [Event],
            ),
            is_internal=True,
        )
        create_rtype(
            (constants.REL_SUB_CAME_EVENT, _('came to the event'), [Contact]),
            (constants.REL_OBJ_CAME_EVENT, _('received'),          [Event]),
            is_internal=True,
        )
        create_rtype(
            (constants.REL_SUB_NOT_CAME_EVENT, _('did not come to the event'), [Contact]),
            (constants.REL_OBJ_NOT_CAME_EVENT, _('did not receive'),           [Event]),
            is_internal=True,
        )
        create_rtype(
            (
                constants.REL_SUB_GEN_BY_EVENT,
                _('generated by the event'),
                [self.Opportunity],
            ), (
                constants.REL_OBJ_GEN_BY_EVENT,
                _('(event) has generated the opportunity'),
                [Event],
            ),
            is_internal=True,
        )

    def _populate_header_filters(self):
        HeaderFilter.objects.create_if_needed(
            pk=constants.DEFAULT_HFILTER_EVENT, name=_('Event view'), model=self.Event,
            cells_desc=[
                (EntityCellRegularField, {'name': 'name'}),
                (EntityCellRegularField, {'name': 'type'}),
                (EntityCellRegularField, {'name': 'start_date'}),
                (EntityCellRegularField, {'name': 'end_date'}),
            ],
        )

    # def _populate_custom_forms(self):
    #     create_cfci = CustomFormConfigItem.objects.create_if_needed
    #     create_cfci(descriptor=custom_forms.EVENT_CREATION_CFORM)
    #     create_cfci(descriptor=custom_forms.EVENT_EDITION_CFORM)

    def _populate_search_config(self):
        SearchConfigItem.objects.create_if_needed(
            model=self.Event, fields=self.SEARCH,
        )

    def _populate_menu_config(self):
        menu_container = MenuConfigItem.objects.get_or_create(
            entry_id=ContainerEntry.id,
            entry_data={'label': _('Tools')},
            role=None, superuser=False,
            defaults={'order': 100},
        )[0]

        MenuConfigItem.objects.create(
            entry_id=EventsEntry.id, parent=menu_container, order=200,
        )

    def _populate_bricks_config(self):
        Event = self.Event
        RIGHT = BrickDetailviewLocation.RIGHT

        BrickDetailviewLocation.objects.multi_create(
            defaults={'model': Event, 'zone': BrickDetailviewLocation.LEFT},
            data=[
                {'order': 5},  # generic info block
                {'brick': core_bricks.CustomFieldsBrick, 'order':  40},
                {'brick': core_bricks.PropertiesBrick,   'order': 450},
                {'brick': core_bricks.RelationsBrick,    'order': 500},

                {'brick': bricks.ResultsBrick,      'order':  2, 'zone': RIGHT},
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
                defaults={'model': Event, 'zone': RIGHT},
                data=[
                    {'brick': a_bricks.TodosBrick,        'order': 100},
                    {'brick': a_bricks.MemosBrick,        'order': 200},
                    {'brick': a_bricks.AlertsBrick,       'order': 300},
                    {'brick': a_bricks.UserMessagesBrick, 'order': 400},
                ]
            )

        if apps.is_installed('creme.documents'):
            # logger.info('Documents app is installed
            # => we use the Documents blocks on detail view')

            from creme.documents.bricks import LinkedDocsBrick

            BrickDetailviewLocation.objects.create_if_needed(
                brick=LinkedDocsBrick, order=600, zone=RIGHT, model=Event,
            )
