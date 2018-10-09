# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

import warnings

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views import generic

from .. import get_ticket_model
from ..constants import DEFAULT_HFILTER_TICKET
from ..forms import ticket as ticket_forms
from ..models import Priority, Criticity


Ticket = get_ticket_model()

# Function views --------------------------------------------------------------


def abstract_add_ticket(request, form=ticket_forms.TicketCreateForm,
                        submit_label=Ticket.save_label,
                       ):
    warnings.warn('tickets.views.ticket.abstract_add_ticket() is deprecated ; '
                  'use the class-based view TicketCreation instead.',
                  DeprecationWarning
                 )
    return generic.add_entity(request, form,
                              extra_initial={'priority':  Priority.objects.first(),
                                             'criticity': Criticity.objects.first(),
                                            },
                              extra_template_dict={'submit_label': submit_label},
                             )


def abstract_edit_ticket(request, ticket_id, form=ticket_forms.TicketEditForm):
    warnings.warn('tickets.views.ticket.abstract_edit_ticket() is deprecated ; '
                  'use the class-based view TicketEdition instead.',
                  DeprecationWarning
                 )
    return generic.edit_entity(request, ticket_id, Ticket, form)


def abstract_view_ticket(request, ticket_id,
                         template='tickets/view_ticket.html',
                        ):
    warnings.warn('tickets.views.ticket.abstract_view_ticket() is deprecated ; '
                  'use the class-based view TicketDetail instead.',
                  DeprecationWarning
                 )
    return generic.view_entity(request, ticket_id, Ticket, template=template)


@login_required
@permission_required(('tickets', cperm(Ticket)))
def add(request):
    warnings.warn('tickets.views.ticket.add() is deprecated.', DeprecationWarning)
    return abstract_add_ticket(request)


@login_required
@permission_required('tickets')
def edit(request, ticket_id):
    warnings.warn('tickets.views.ticket.edit() is deprecated.', DeprecationWarning)
    return abstract_edit_ticket(request, ticket_id)


@login_required
@permission_required('tickets')
def detailview(request, ticket_id):
    warnings.warn('tickets.views.ticket.detailview() is deprecated.', DeprecationWarning)
    return abstract_view_ticket(request, ticket_id)


@login_required
@permission_required('tickets')
def listview(request):
    return generic.list_view(request, Ticket, hf_pk=DEFAULT_HFILTER_TICKET)


# Class-based views  ----------------------------------------------------------

class TicketCreation(generic.EntityCreation):
    model = Ticket
    form_class = ticket_forms.TicketCreateForm

    def get_initial(self):
        initial = super().get_initial()
        initial['priority']  = Priority.objects.first()
        initial['criticity'] = Criticity.objects.first()

        return initial


class TicketDetail(generic.EntityDetail):
    model = Ticket
    template_name = 'tickets/view_ticket.html'
    pk_url_kwarg = 'ticket_id'


class TicketEdition(generic.EntityEdition):
    model = Ticket
    form_class = ticket_forms.TicketEditForm
    pk_url_kwarg = 'ticket_id'
