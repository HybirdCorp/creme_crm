# -*- coding: utf-8 -*-

from django.contrib.auth.decorators import login_required, permission_required

from creme_core.views.generic import add_entity, edit_entity, view_entity_with_template, list_view

from tickets.models.ticket import Ticket
from tickets.forms.ticket import CreateForm, EditForm


@login_required
@permission_required('tickets')
@permission_required('tickets.add_ticket')
def add(request):
    return add_entity(request, CreateForm)

def edit(request, ticket_id):
    return edit_entity(request, ticket_id, Ticket, EditForm, 'tickets')

@login_required
@permission_required('tickets')
def detailview(request, ticket_id):
    return view_entity_with_template(request, ticket_id, Ticket,
                                     '/tickets/ticket',
                                     'tickets/view_ticket.html')

@login_required
@permission_required('tickets')
def listview(request):
    return list_view(request, Ticket, extra_dict={'add_url': '/tickets/ticket/add'})
