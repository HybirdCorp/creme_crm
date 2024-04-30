################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2024  Hybird
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

from creme.creme_core.views import generic

from .. import custom_forms, get_ticket_model
from ..constants import DEFAULT_HFILTER_TICKET
from ..models import Criticity, Priority

Ticket = get_ticket_model()


class TicketCreation(generic.EntityCreation):
    model = Ticket
    form_class = custom_forms.TICKET_CREATION_CFORM

    def get_initial(self):
        initial = super().get_initial()
        initial['priority'] = Priority.objects.first()
        initial['criticity'] = Criticity.objects.first()

        return initial


class TicketDetail(generic.EntityDetail):
    model = Ticket
    template_name = 'tickets/view_ticket.html'
    pk_url_kwarg = 'ticket_id'


class TicketEdition(generic.EntityEdition):
    model = Ticket
    form_class = custom_forms.TICKET_EDITION_CFORM
    pk_url_kwarg = 'ticket_id'


class TicketsList(generic.EntitiesList):
    model = Ticket
    default_headerfilter_id = DEFAULT_HFILTER_TICKET

    def get_unordered_queryset_n_count(self):
        qs, count = super().get_unordered_queryset_n_count()

        # NB1: select_related() to avoid queries when the field status is not
        #      in the columns of the HeaderFilter (see AbstractTicket.get_html_attrs()).
        # NB2: it's OK to modify the base queryset here because we are not filtering it.
        return qs.select_related('status'), count
