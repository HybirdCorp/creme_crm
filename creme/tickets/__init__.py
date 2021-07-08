# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2021  Hybird
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

from django.conf import settings

from creme.creme_core import get_concrete_model


def ticket_model_is_custom():
    return (
        settings.TICKETS_TICKET_MODEL != 'tickets.Ticket'
        and not settings.TICKETS_TICKET_FORCE_NOT_CUSTOM
    )


def tickettemplate_model_is_custom():
    return (
        settings.TICKETS_TEMPLATE_MODEL != 'tickets.TicketTemplate'
        and not settings.TICKETS_TEMPLATE_FORCE_NOT_CUSTOM
    )


def get_ticket_model():
    """Returns the Ticket model that is active in this project."""
    return get_concrete_model('TICKETS_TICKET_MODEL')


def get_tickettemplate_model():
    """Returns the TicketTemplate model that is active in this project."""
    return get_concrete_model('TICKETS_TEMPLATE_MODEL')


# default_app_config = 'creme.tickets.apps.TicketsConfig'
