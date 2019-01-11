# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2018  Hybird
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
    verbose_name = _('Tickets')
    dependencies = ['creme.creme_core']

    def all_apps_ready(self):
        from . import get_ticket_model, get_tickettemplate_model

        self.Ticket         = get_ticket_model()
        self.TicketTemplate = get_tickettemplate_model()
        super().all_apps_ready()

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.Ticket)

    def register_bricks(self, brick_registry):
        from .bricks import TicketBrick

        brick_registry.register_4_model(self.Ticket, TicketBrick)

    def register_buttons(self, button_registry):
        from . import buttons

        button_registry.register(buttons.Linked2TicketButton)

    def register_function_fields(self, function_field_registry):
        from .function_fields import ResolvingDurationField

        function_field_registry.register(self.Ticket, ResolvingDurationField)

    def register_icons(self, icon_registry):
        reg_icon = icon_registry.register
        reg_icon(self.Ticket,         'images/ticket_%(size)s.png')
        reg_icon(self.TicketTemplate, 'images/ticket_%(size)s.png')

    def register_mass_import(self, import_form_registry):
        import_form_registry.register(self.Ticket)

    def register_menu(self, creme_menu):
        Ticket = self.Ticket
        creme_menu.get('features', 'tools') \
                  .add(creme_menu.URLItem.list_view('tickets-tickets', model=Ticket), priority=100)
        creme_menu.get('creation', 'any_forms') \
                  .get_or_create_group('tools', _('Tools'), priority=100) \
                  .add_link('tickets-create_ticket', Ticket, priority=100)

    def register_smart_columns(self, smart_columns_registry):
        smart_columns_registry.register_model(self.Ticket).register_field('title') \
                                                          .register_field('status')

    def register_statistics(self, statistics_registry):
        from .models.status import CLOSED_PK

        statistics_registry.register(
            id='tickets-not_closed',
            label=_('Tickets not closed'),
            func=lambda: [self.Ticket.objects.exclude(status_id=CLOSED_PK).count()],
            perm='tickets', priority=50,
        )
