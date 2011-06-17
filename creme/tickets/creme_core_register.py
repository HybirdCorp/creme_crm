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

from django.utils.translation import ugettext_lazy as _

from creme_core.registry import creme_registry
from creme_core.gui import creme_menu, block_registry, button_registry, icon_registry, bulk_update_registry

from tickets.models import Ticket, TicketTemplate
from tickets.blocks import TicketBlock
from tickets.buttons import linked_2_ticket_button


creme_registry.register_app('tickets', _(u'Tickets'), '/tickets')
creme_registry.register_entity_models(Ticket)

reg_item = creme_menu.register_app('tickets', '/tickets/').register_item
reg_item('/tickets/',           _(u'Portal'),       'tickets')
reg_item('/tickets/tickets',    _(u'All tickets'),  'tickets')
reg_item('/tickets/ticket/add', _(u'Add a ticket'), 'tickets.add_ticket')

block_registry.register_4_model(Ticket, TicketBlock())

button_registry.register(linked_2_ticket_button)

reg_icon = icon_registry.register
reg_icon(Ticket,         'images/ticket_%(size)s.png')
reg_icon(TicketTemplate, 'images/ticket_%(size)s.png')

bulk_update_registry.register(
    (Ticket, ['title', 'status']),
)