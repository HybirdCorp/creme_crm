# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from creme.creme_core import bricks as core_bricks
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.forms import LAYOUT_DUAL_FIRST, LAYOUT_DUAL_SECOND
from creme.creme_core.gui.custom_form import EntityCellCustomFormSpecial
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

    def populate(self):
        already_populated = RelationType.objects.filter(
            pk=constants.REL_SUB_LINKED_2_TICKET,
        ).exists()

        Ticket = get_ticket_model()
        TicketTemplate = get_tickettemplate_model()

        RelationType.objects.smart_update_or_create(
            (constants.REL_SUB_LINKED_2_TICKET, _('is linked to the ticket')),
            (constants.REL_OBJ_LINKED_2_TICKET, _('(ticket) linked to the entity'), [Ticket]),
        )

        if apps.is_installed('creme.activities'):
            logger.info(
                'Activities app is installed => a Ticket can be the subject of an Activity'
            )

            from creme.activities.constants import REL_SUB_ACTIVITY_SUBJECT

            RelationType.objects.get(pk=REL_SUB_ACTIVITY_SUBJECT).add_subject_ctypes(Ticket)

        # ---------------------------
        for pk, name, is_closed in BASE_STATUS:
            create_if_needed(
                Status,
                {'pk': pk},
                name=str(name),
                is_closed=is_closed,
                is_custom=False,
                order=pk,
            )

        # ---------------------------
        create_hf = HeaderFilter.objects.create_if_needed
        create_hf(
            pk=constants.DEFAULT_HFILTER_TICKET,
            model=Ticket,
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
            model=TicketTemplate,
            name=_('Ticket template view'),
            cells_desc=[
                (EntityCellRegularField, {'name': 'title'}),
                (EntityCellRegularField, {'name': 'status'}),
                (EntityCellRegularField, {'name': 'priority'}),
                (EntityCellRegularField, {'name': 'criticity'}),
            ],
        )

        # ---------------------------
        common_groups_desc = [
            {
                'name': _('Description'),
                'layout': LAYOUT_DUAL_SECOND,
                'cells': [
                    (EntityCellRegularField, {'name': 'description'}),
                ],
            }, {
                'name': _('Custom fields'),
                'layout': LAYOUT_DUAL_SECOND,
                'cells': [
                    (
                        EntityCellCustomFormSpecial,
                        {'name': EntityCellCustomFormSpecial.REMAINING_CUSTOMFIELDS},
                    ),
                ],
            },
        ]
        creation_only_groups_desc = [
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
        ]

        CustomFormConfigItem.objects.create_if_needed(
            descriptor=custom_forms.TICKET_CREATION_CFORM,
            groups_desc=[
                {
                    'name': _('General information'),
                    'layout': LAYOUT_DUAL_FIRST,
                    'cells': [
                        (EntityCellRegularField, {'name': 'user'}),
                        (EntityCellRegularField, {'name': 'title'}),
                        (EntityCellRegularField, {'name': 'priority'}),
                        (EntityCellRegularField, {'name': 'criticity'}),
                        (EntityCellRegularField, {'name': 'solution'}),
                        (
                            EntityCellCustomFormSpecial,
                            {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                        ),
                    ],
                },
                *common_groups_desc,
                *creation_only_groups_desc,
            ],
        )
        CustomFormConfigItem.objects.create_if_needed(
            descriptor=custom_forms.TICKET_EDITION_CFORM,
            groups_desc=[
                {
                    'name': _('General information'),
                    'cells': [
                        (EntityCellRegularField, {'name': 'user'}),
                        (EntityCellRegularField, {'name': 'title'}),
                        (EntityCellRegularField, {'name': 'status'}),
                        (EntityCellRegularField, {'name': 'priority'}),
                        (EntityCellRegularField, {'name': 'criticity'}),
                        (EntityCellRegularField, {'name': 'solution'}),
                        (
                            EntityCellCustomFormSpecial,
                            {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                        ),
                    ],
                },
                *common_groups_desc,
            ],
        )

        template_rfields_group_desc = {
            'name': _('General information'),
            'cells': [
                (EntityCellRegularField, {'name': 'user'}),
                (EntityCellRegularField, {'name': 'title'}),
                (EntityCellRegularField, {'name': 'status'}),
                (EntityCellRegularField, {'name': 'priority'}),
                (EntityCellRegularField, {'name': 'criticity'}),
                (EntityCellRegularField, {'name': 'solution'}),
                (
                    EntityCellCustomFormSpecial,
                    {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                ),
            ],
        }

        CustomFormConfigItem.objects.create_if_needed(
            descriptor=custom_forms.TTEMPLATE_CREATION_CFORM,
            groups_desc=[
                template_rfields_group_desc,
                *common_groups_desc,
                *creation_only_groups_desc,
            ],
        )
        CustomFormConfigItem.objects.create_if_needed(
            descriptor=custom_forms.TTEMPLATE_EDITION_CFORM,
            groups_desc=[
                template_rfields_group_desc,
                *common_groups_desc,
            ],
        )

        # ---------------------------
        SearchConfigItem.objects.create_if_needed(
            Ticket,
            [
                'title',
                'number',
                'description',
                'status__name',
                'priority__name',
                'criticity__name',
            ],
        )

        # ---------------------------
        # TODO: move to "not already_populated" section in creme2.4
        if not MenuConfigItem.objects.filter(entry_id__startswith='tickets-').exists():
            container = MenuConfigItem.objects.get_or_create(
                entry_id=ContainerEntry.id,
                entry_data={'label': _('Tools')},
                defaults={'order': 100},
            )[0]

            MenuConfigItem.objects.create(
                entry_id=TicketsEntry.id, parent=container, order=100,
            )

        # ---------------------------
        if not already_populated:
            for model in (Ticket, TicketTemplate):
                FieldsConfig.objects.create(
                    content_type=model,
                    descriptions=[('description', {FieldsConfig.REQUIRED: True})],
                )

            for i, name in enumerate(
                [_('Low'), _('Normal'), _('High'), _('Urgent'), _('Blocking')],
                start=1,
            ):
                create_if_needed(Priority, {'pk': i}, name=name, order=i)

            for i, name in enumerate(
                [
                    _('Minor'), _('Major'),
                    _('Feature'), _('Critical'), _('Enhancement'),
                    _('Error')
                ],
                start=1,
            ):
                create_if_needed(Criticity, {'pk': i}, name=name, order=i)

            # ---------------------------
            rbi = RelationBrickItem.objects.create_if_needed(constants.REL_OBJ_LINKED_2_TICKET)

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

                from creme.assistants import bricks as a_bricks

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

            # ---------------------------
            if apps.is_installed('creme.persons'):
                try:
                    from creme.persons import (
                        get_contact_model,
                        get_organisation_model,
                    )
                except ImportError as e:
                    logger.info(str(e))
                else:
                    from creme.tickets.buttons import Linked2TicketButton

                    logger.info(
                        "'Persons' app is installed "
                        "=> add button 'Linked to a ticket' to Contact & Organisation"
                    )

                    create_bmi = ButtonMenuItem.objects.create_if_needed
                    for model in (get_contact_model(), get_organisation_model()):
                        create_bmi(model=model, button=Linked2TicketButton, order=50)
