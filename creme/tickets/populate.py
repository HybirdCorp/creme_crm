# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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
from django.utils.translation import ugettext as _

from creme.creme_core import bricks as core_bricks
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (RelationType, HeaderFilter,
        SearchConfigItem, BrickDetailviewLocation, RelationBrickItem, ButtonMenuItem)
from creme.creme_core.utils import create_if_needed

from . import constants, get_ticket_model, get_tickettemplate_model
from .models import Status, Priority, Criticity
from .models.status import BASE_STATUS


logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core', 'activities']

    def populate(self):
        already_populated = RelationType.objects.filter(pk=constants.REL_SUB_LINKED_2_TICKET).exists()

        Ticket = get_ticket_model()
        TicketTemplate = get_tickettemplate_model()

        RelationType.create((constants.REL_SUB_LINKED_2_TICKET, _(u'is linked to the ticket')),
                            (constants.REL_OBJ_LINKED_2_TICKET, _(u'(ticket) linked to the entity'), [Ticket]))

        if apps.is_installed('creme.activities'):
            logger.info('Activities app is installed => a Ticket can be the subject of an Activity')

            from creme.activities.constants import REL_SUB_ACTIVITY_SUBJECT

            RelationType.objects.get(pk=REL_SUB_ACTIVITY_SUBJECT).add_subject_ctypes(Ticket)

        # ---------------------------
        for pk, name in BASE_STATUS:
            create_if_needed(Status, {'pk': pk}, name=str(name), is_custom=False, order=pk)

        # ---------------------------
        create_hf = HeaderFilter.create
        create_hf(pk=constants.DEFAULT_HFILTER_TICKET,
                  model=Ticket,
                  name=_(u'Ticket view'),
                  cells_desc=[(EntityCellRegularField, {'name': 'number'}),
                              (EntityCellRegularField, {'name': 'title'}),
                              (EntityCellRegularField, {'name': 'status'}),
                              (EntityCellRegularField, {'name': 'priority'}),
                              (EntityCellRegularField, {'name': 'criticity'}),
                              (EntityCellRegularField, {'name': 'closing_date'}),
                             ],
                 )
        create_hf(pk=constants.DEFAULT_HFILTER_TTEMPLATE,
                  model=TicketTemplate,
                  name=_(u'Ticket template view'),
                  cells_desc=[(EntityCellRegularField, {'name': 'title'}),
                              (EntityCellRegularField, {'name': 'status'}),
                              (EntityCellRegularField, {'name': 'priority'}),
                              (EntityCellRegularField, {'name': 'criticity'}),
                             ],
                 )

        # ---------------------------
        SearchConfigItem.create_if_needed(Ticket,
                                          ['title', 'number', 'description',
                                           'status__name', 'priority__name', 'criticity__name',
                                          ]
                                         )

        # ---------------------------
        if not already_populated:
            for i, name in enumerate([_(u'Low'), _(u'Normal'), _(u'High'), _(u'Urgent'), _(u'Blocking')], start=1):
                create_if_needed(Priority, {'pk': i}, name=name, order=i)

            for i, name in enumerate([_(u'Minor'), _(u'Major'), _(u'Feature'), _(u'Critical'), _(u'Enhancement'), _(u'Error')], start=1):
                create_if_needed(Criticity, {'pk': i}, name=name, order=i)

            # ---------------------------
            rbi = RelationBrickItem.create(constants.REL_OBJ_LINKED_2_TICKET)

            create_bdl = BrickDetailviewLocation.create_if_needed
            LEFT  = BrickDetailviewLocation.LEFT
            RIGHT = BrickDetailviewLocation.RIGHT

            BrickDetailviewLocation.create_4_model_brick(          order=5,   zone=LEFT,  model=Ticket)
            create_bdl(brick_id=core_bricks.CustomFieldsBrick.id_, order=40,  zone=LEFT,  model=Ticket)
            create_bdl(brick_id=core_bricks.PropertiesBrick.id_,   order=450, zone=LEFT,  model=Ticket)
            create_bdl(brick_id=core_bricks.RelationsBrick.id_,    order=500, zone=LEFT,  model=Ticket)
            create_bdl(brick_id=rbi.brick_id,                      order=1,   zone=RIGHT, model=Ticket)
            create_bdl(brick_id=core_bricks.HistoryBrick.id_,      order=20,  zone=RIGHT, model=Ticket)

            if apps.is_installed('creme.assistants'):
                logger.info('Assistants app is installed => we use the assistants blocks on detail view')

                from creme.assistants import bricks as a_bricks

                create_bdl(brick_id=a_bricks.TodosBrick.id_,        order=100, zone=RIGHT, model=Ticket)
                create_bdl(brick_id=a_bricks.MemosBrick.id_,        order=200, zone=RIGHT, model=Ticket)
                create_bdl(brick_id=a_bricks.AlertsBrick.id_,       order=300, zone=RIGHT, model=Ticket)
                create_bdl(brick_id=a_bricks.UserMessagesBrick.id_, order=400, zone=RIGHT, model=Ticket)

            if apps.is_installed('creme.documents'):
                # logger.info("Documents app is installed => we use the documents block on Ticket's detail views")

                from creme.documents.bricks import LinkedDocsBrick

                create_bdl(brick_id=LinkedDocsBrick.id_, order=600, zone=RIGHT, model=Ticket)

            # ---------------------------
            if apps.is_installed('creme.persons'):
                try:
                    from creme.persons import get_contact_model, get_organisation_model
                except ImportError as e:
                    logger.info(str(e))
                else:
                    from creme.tickets.buttons import Linked2TicketButton

                    create_bmi = ButtonMenuItem.create_if_needed
                    create_bmi(pk='tickets-linked_contact_button', model=get_contact_model(),      button=Linked2TicketButton, order=50)
                    create_bmi(pk='tickets-linked_orga_button',    model=get_organisation_model(), button=Linked2TicketButton, order=50)

                    logger.info("'Persons' app is installed => add button 'Linked to a ticket' to Contact & Organisation")
