# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from logging import info

from django.utils.translation import ugettext as _
from django.conf import settings

from creme_core.models import (RelationType, SearchConfigItem, HeaderFilterItem, HeaderFilter,
                               BlockDetailviewLocation, RelationBlockItem, ButtonMenuItem) #BlockConfigItem
from creme_core.utils import create_or_update as create
from creme_core.management.commands.creme_populate import BasePopulator

from tickets.models import *
from tickets.models.status import BASE_STATUS
from tickets.constants import REL_SUB_LINKED_2_TICKET, REL_OBJ_LINKED_2_TICKET


class Populator(BasePopulator):
    dependencies = ['creme.creme_core']

    def populate(self, *args, **kwargs):
        RelationType.create((REL_SUB_LINKED_2_TICKET, _(u'is linked to the ticket')),
                            (REL_OBJ_LINKED_2_TICKET, _(u'(ticket) linked to the entitity'), [Ticket]))

        for pk, name in BASE_STATUS:
            create(Status, pk, name=name, is_custom=False)

        #TODO: use 'start' arg with python 2.6.....
        for i, name in enumerate((_('Low'), _('Normal'), _('High'), _('Urgent'), _('Blocking'))):
            create(Priority, i + 1, name=name)

        for i, name in enumerate((_('Minor'), _('Major'), _('Feature'), _('Critical'), _('Enhancement'), _('Error'))):
            create(Criticity, i + 1, name=name)

        hf = HeaderFilter.create(pk='tickets-hf_ticket', name=_(u'Ticket view'), model=Ticket)
        hf.set_items([HeaderFilterItem.build_4_field(model=Ticket, name='title'),
                      HeaderFilterItem.build_4_field(model=Ticket, name='status__name'),
                      HeaderFilterItem.build_4_field(model=Ticket, name='priority__name'),
                      HeaderFilterItem.build_4_field(model=Ticket, name='criticity__name'),
                      HeaderFilterItem.build_4_field(model=Ticket, name='closing_date'),
                     ])

        hf = HeaderFilter.create(pk='tickets-hf_template', name=_(u'Ticket template view'), model=TicketTemplate)
        hf.set_items([HeaderFilterItem.build_4_field(model=TicketTemplate, name='title'),
                      HeaderFilterItem.build_4_field(model=TicketTemplate, name='status__name'),
                      HeaderFilterItem.build_4_field(model=TicketTemplate, name='priority__name'),
                      HeaderFilterItem.build_4_field(model=TicketTemplate, name='criticity__name'),
                     ])

        SearchConfigItem.create(Ticket, ['title', 'description', 'status__name', 'priority__name', 'criticity__name'])

        rbi = RelationBlockItem.create(REL_OBJ_LINKED_2_TICKET)
        #BlockConfigItem.create(pk='tickets-linked2_block',  model=Ticket, block_id=rbi.block_id, order=1, on_portal=False)
        BlockDetailviewLocation.create(block_id=rbi.block_id, order=1, zone=BlockDetailviewLocation.RIGHT, model=Ticket)

        if 'creme.persons' in settings.INSTALLED_APPS:
            try:
                from persons.models import Contact, Organisation
            except ImportError, e:
                info(str(e))
            else:
                from tickets.buttons import linked_2_ticket_button

                ButtonMenuItem.create(pk='tickets-linked_contact_button', model=Contact,      button=linked_2_ticket_button, order=50)
                ButtonMenuItem.create(pk='tickets-linked_orga_button',    model=Organisation, button=linked_2_ticket_button, order=50)

                info("'Persons' app is installed => add button 'Linked to a ticket' to Contact & Organisation")
