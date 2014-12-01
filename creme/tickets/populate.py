# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from django.conf import settings
from django.utils.translation import ugettext as _

from creme.creme_core.blocks import (properties_block, relations_block,
        customfields_block, history_block)
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (RelationType, HeaderFilter,
        SearchConfigItem, BlockDetailviewLocation, RelationBlockItem, ButtonMenuItem)
from creme.creme_core.utils import create_if_needed

from .models import *
from .models.status import BASE_STATUS
from .constants import REL_SUB_LINKED_2_TICKET, REL_OBJ_LINKED_2_TICKET


logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core', 'activities']

    def populate(self):
        already_populated = RelationType.objects.filter(pk=REL_SUB_LINKED_2_TICKET).exists()

        RelationType.create((REL_SUB_LINKED_2_TICKET, _(u'is linked to the ticket')),
                            (REL_OBJ_LINKED_2_TICKET, _(u'(ticket) linked to the entity'), [Ticket]))

        if 'creme.activities' in settings.INSTALLED_APPS:
            logger.info('Activities app is installed => a Ticket can be the subject of an Activity')

            from creme.activities.constants import REL_SUB_ACTIVITY_SUBJECT

            RelationType.objects.get(pk=REL_SUB_ACTIVITY_SUBJECT).add_subject_ctypes(Ticket)


        for pk, name in BASE_STATUS:
            create_if_needed(Status, {'pk': pk}, name=unicode(name), is_custom=False, order=pk)


        create_hf = HeaderFilter.create
        create_hf(pk='tickets-hf_ticket', name=_(u'Ticket view'), model=Ticket,
                  cells_desc=[(EntityCellRegularField, {'name': 'title'}),
                              (EntityCellRegularField, {'name': 'status'}),
                              (EntityCellRegularField, {'name': 'priority'}),
                              (EntityCellRegularField, {'name': 'criticity'}),
                              (EntityCellRegularField, {'name': 'closing_date'}),
                             ],
                 )
        create_hf(pk='tickets-hf_template', name=_(u'Ticket template view'), model=TicketTemplate,
                  cells_desc=[(EntityCellRegularField, {'name': 'title'}),
                              (EntityCellRegularField, {'name': 'status'}),
                              (EntityCellRegularField, {'name': 'priority'}),
                              (EntityCellRegularField, {'name': 'criticity'}),
                             ],
                 )


        SearchConfigItem.create_if_needed(Ticket, ['title', 'description', 'status__name', 'priority__name', 'criticity__name'])


        if not already_populated:
            for i, name in enumerate([_('Low'), _('Normal'), _('High'), _('Urgent'), _('Blocking')], start=1):
                create_if_needed(Priority, {'pk': i}, name=name, order=i)

            for i, name in enumerate([_('Minor'), _('Major'), _('Feature'), _('Critical'), _('Enhancement'), _('Error')], start=1):
                create_if_needed(Criticity, {'pk': i}, name=name, order=i)


            rbi = RelationBlockItem.create(REL_OBJ_LINKED_2_TICKET)

            BlockDetailviewLocation.create_4_model_block(order=5, zone=BlockDetailviewLocation.LEFT, model=Ticket)
            create_bdl = BlockDetailviewLocation.create
            create_bdl(block_id=customfields_block.id_, order=40,  zone=BlockDetailviewLocation.LEFT,  model=Ticket)
            create_bdl(block_id=properties_block.id_,   order=450, zone=BlockDetailviewLocation.LEFT,  model=Ticket)
            create_bdl(block_id=relations_block.id_,    order=500, zone=BlockDetailviewLocation.LEFT,  model=Ticket)
            create_bdl(block_id=rbi.block_id,           order=1,   zone=BlockDetailviewLocation.RIGHT, model=Ticket)
            create_bdl(block_id=history_block.id_,      order=20,  zone=BlockDetailviewLocation.RIGHT, model=Ticket)


            if 'creme.assistants' in settings.INSTALLED_APPS:
                logger.info('Assistants app is installed => we use the assistants blocks on detail view')

                from creme.assistants.blocks import alerts_block, memos_block, todos_block, messages_block

                create_bdl(block_id=todos_block.id_,    order=100, zone=BlockDetailviewLocation.RIGHT, model=Ticket)
                create_bdl(block_id=memos_block.id_,    order=200, zone=BlockDetailviewLocation.RIGHT, model=Ticket)
                create_bdl(block_id=alerts_block.id_,   order=300, zone=BlockDetailviewLocation.RIGHT, model=Ticket)
                create_bdl(block_id=messages_block.id_, order=400, zone=BlockDetailviewLocation.RIGHT, model=Ticket)


            if 'creme.persons' in settings.INSTALLED_APPS:
                try:
                    from creme.persons.models import Contact, Organisation
                except ImportError as e:
                    logger.info(str(e))
                else:
                    from creme.tickets.buttons import linked_2_ticket_button

                    create_bmi = ButtonMenuItem.create_if_needed
                    create_bmi(pk='tickets-linked_contact_button', model=Contact,      button=linked_2_ticket_button, order=50)
                    create_bmi(pk='tickets-linked_orga_button',    model=Organisation, button=linked_2_ticket_button, order=50)

                    logger.info("'Persons' app is installed => add button 'Linked to a ticket' to Contact & Organisation")
