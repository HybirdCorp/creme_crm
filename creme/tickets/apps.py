# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015  Hybird
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

from creme.creme_core.apps import CremeAppConfig


class TicketsConfig(CremeAppConfig):
    name = 'creme.tickets'
    verbose_name = _(u'Tickets')
    dependencies = ['creme.creme_core']

    def ready(self):
        from . import get_ticket_model, get_tickettemplate_model

        self.Ticket         = get_ticket_model()
        self.TicketTemplate = get_tickettemplate_model()
        super(TicketsConfig, self).ready()

    def register_creme_app(self, creme_registry):
        creme_registry.register_app('tickets', _(u'Tickets'), '/tickets')

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.Ticket)

    def register_blocks(self, block_registry):
        from .blocks import TicketBlock

        block_registry.register_4_model(self.Ticket, TicketBlock())

    def register_buttons(self, button_registry):
        from .buttons import linked_2_ticket_button

        button_registry.register(linked_2_ticket_button)

    def register_icons(self, icon_registry):
        reg_icon = icon_registry.register
        reg_icon(self.Ticket,         'images/ticket_%(size)s.png')
        reg_icon(self.TicketTemplate, 'images/ticket_%(size)s.png')

    def register_mass_import(self, import_form_registry):
        import_form_registry.register(self.Ticket)

    def register_menu(self, creme_menu):
        from django.core.urlresolvers import reverse_lazy as reverse

        from creme.creme_core.auth import build_creation_perm as cperm

        Ticket = self.Ticket
        reg_item = creme_menu.register_app('tickets', '/tickets/').register_item
        reg_item('/tickets/',                       _(u'Portal of tickets'), 'tickets')
        reg_item(reverse('tickets__list_tickets'),  _(u'All tickets'),       'tickets')
        reg_item(reverse('tickets__create_ticket'), Ticket.creation_label,   cperm(Ticket))

    def register_smart_columns(self, smart_columns_registry):
        smart_columns_registry.register_model(self.Ticket).register_field('title') \
                                                          .register_field('status')
