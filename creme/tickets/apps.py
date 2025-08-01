################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2025  Hybird
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

from django.utils.translation import gettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class TicketsConfig(CremeAppConfig):
    default = True
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

    def register_bulk_update(self, bulk_update_registry):
        register = bulk_update_registry.register
        register(self.Ticket)
        register(self.TicketTemplate)

    def register_buttons(self, button_registry):
        from . import buttons

        button_registry.register(buttons.Linked2TicketButton)

    def register_creme_config(self, config_registry):
        from . import models

        register_model = config_registry.register_model
        register_model(models.Status,    'status')
        register_model(models.Priority,  'priority')
        register_model(models.Criticity, 'criticity')

    def register_custom_forms(self, cform_registry):
        from . import custom_forms

        cform_registry.register(
            custom_forms.TICKET_CREATION_CFORM,
            custom_forms.TICKET_EDITION_CFORM,

            custom_forms.TTEMPLATE_CREATION_CFORM,
            custom_forms.TTEMPLATE_EDITION_CFORM,
        )

    def register_cloners(self, entity_cloner_registry):
        entity_cloner_registry.register(model=self.Ticket)
        # NB: TicketTemplates can not be cloned
        #     (because they are closely linked to their RecurrentGenerator)

    def register_deletors(self, entity_deletor_registry):
        entity_deletor_registry.register(model=self.Ticket)
        # NB: TicketTemplates can not be deleted directly
        #     (because they are closely linked to their RecurrentGenerator)

    def register_fields_config(self, fields_config_registry):
        fields_config_registry.register_models(
            self.Ticket,
            self.TicketTemplate,
        )

    def register_field_printers(self, field_printer_registry):
        from django.db.models import ForeignKey

        from creme.creme_core.gui.field_printers import FKPrinter

        from .models import Status

        # TODO: models.OneToOneField? ManyToManyField?
        for printer in field_printer_registry.printers_for_field_type(
            type=ForeignKey, tags='html*',
        ):
            printer.register(model=Status, printer=FKPrinter.print_fk_colored_html)

    def register_function_fields(self, function_field_registry):
        from .function_fields import ResolvingDurationField

        function_field_registry.register(self.Ticket, ResolvingDurationField)

    def register_icons(self, icon_registry):
        icon_registry.register(
            self.Ticket,         'images/ticket_%(size)s.png',
        ).register(
            self.TicketTemplate, 'images/ticket_%(size)s.png',
        )

    def register_mass_import(self, import_form_registry):
        import_form_registry.register(self.Ticket)

    def register_menu_entries(self, menu_registry):
        from . import menu

        menu_registry.register(
            menu.TicketsEntry,
            menu.TicketCreationEntry,
        )

    def register_creation_menu(self, creation_menu_registry):
        creation_menu_registry.get_or_create_group(
            'tools', _('Tools'), priority=100,
        ).add_link(
            'tickets-create_ticket', self.Ticket, priority=100,
        )

    def register_smart_columns(self, smart_columns_registry):
        smart_columns_registry.register_model(
            self.Ticket
        ).register_field('title').register_field('status')

    def register_statistics(self, statistic_registry):
        statistic_registry.register(
            id='tickets-not_closed',
            label=_('Tickets not closed'),
            func=lambda: [self.Ticket.objects.exclude(status__is_closed=True).count()],
            perm='tickets', priority=50,
        )
