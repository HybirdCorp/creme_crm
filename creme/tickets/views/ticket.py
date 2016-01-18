# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views.generic import add_entity, edit_entity, view_entity, list_view

from .. import get_ticket_model
from ..constants import DEFAULT_HFILTER_TICKET
from ..forms.ticket import TicketCreateForm, TicketEditForm
from ..models import Priority, Criticity


Ticket = get_ticket_model()


def abstract_add_ticket(request, form=TicketCreateForm,
                        submit_label=_('Save the ticket'),
                       ):
    return add_entity(request, form,
                      extra_initial={'priority':  Priority.objects.first(),
                                     'criticity': Criticity.objects.first(),
                                    },
                      extra_template_dict={'submit_label': submit_label},
                     )


def abstract_edit_ticket(request, ticket_id, form=TicketEditForm):
    return edit_entity(request, ticket_id, Ticket, form)


def abstract_view_ticket(request, ticket_id,
                         template='tickets/view_ticket.html',
                        ):
    return view_entity(request, ticket_id, Ticket, template=template)


@login_required
@permission_required(('tickets', cperm(Ticket)))
def add(request):
    return abstract_add_ticket(request)


@login_required
@permission_required('tickets')
def edit(request, ticket_id):
    return abstract_edit_ticket(request, ticket_id)


@login_required
@permission_required('tickets')
def detailview(request, ticket_id):
    return abstract_view_ticket(request, ticket_id)


@login_required
@permission_required('tickets')
def listview(request):
    return list_view(request, Ticket, hf_pk=DEFAULT_HFILTER_TICKET)
