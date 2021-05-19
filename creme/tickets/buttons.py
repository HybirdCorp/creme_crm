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

from django.utils.translation import gettext_lazy as _

from creme.creme_core.gui.button_menu import Button

from .constants import REL_SUB_LINKED_2_TICKET


class Linked2TicketButton(Button):
    id_ = Button.generate_id('tickets', 'linked2ticket')
    verbose_name = _('Is linked to a ticket')
    description = _(
        'This button links the current entity to a selected ticket, '
        'using the relationship type «is linked to the ticket».\n'
        'App: Tickets'
    )
    template_name = 'tickets/buttons/linked.html'
    # permission = 'tickets'
    permissions = 'tickets'

    def render(self, context):
        context['rtype_id'] = REL_SUB_LINKED_2_TICKET

        return super().render(context)
