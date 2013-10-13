# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from django.contrib.auth.decorators import login_required, permission_required
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.views.generic import add_entity, edit_entity, view_entity, list_view
from creme.creme_core.utils.queries import get_first_or_None

from ..models import Ticket, Priority, Criticity
from ..forms.ticket import TicketCreateForm, TicketEditForm


@login_required
@permission_required('tickets')
@permission_required('tickets.add_ticket')
def add(request):
    return add_entity(request, TicketCreateForm,
                      extra_initial={'priority':  get_first_or_None(Priority),
                                     'criticity': get_first_or_None(Criticity),
                                    },
                      extra_template_dict={'submit_label': _('Save the ticket')},
                     )

@login_required
@permission_required('tickets')
def edit(request, ticket_id):
    return edit_entity(request, ticket_id, Ticket, TicketEditForm)

@login_required
@permission_required('tickets')
def detailview(request, ticket_id):
    return view_entity(request, ticket_id, Ticket, '/tickets/ticket', 'tickets/view_ticket.html')

@login_required
@permission_required('tickets')
def listview(request):
    return list_view(request, Ticket, extra_dict={'add_url': '/tickets/ticket/add'})
