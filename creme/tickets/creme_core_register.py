# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme_core.registry import creme_registry
from creme_core.gui.menu import creme_menu
from creme_core.gui.button_menu import button_registry
from creme_core.gui.bulk_update import bulk_update_registry

from tickets.models import Ticket
from tickets.buttons import linked_2_ticket_button


creme_registry.register_app('tickets', _(u'Tickets'), '/tickets')
creme_registry.register_entity_models(Ticket)

reg_item = creme_menu.register_app('tickets', '/tickets/').register_item
reg_item('/tickets/',           _(u'Portal'),       'tickets')
reg_item('/tickets/tickets',    _(u'All tickets'),  'tickets')
reg_item('/tickets/ticket/add', _(u'Add a ticket'), 'tickets.add_ticket')

button_registry.register(linked_2_ticket_button)

bulk_update_registry.register(
    (Ticket, ['title']),
)