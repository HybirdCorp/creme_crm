# -*- coding: utf-8 -*-

from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType

from creme_core.entities_access.functions_for_permissions import add_view_or_die, get_view_or_die
from creme_core.views.generic import add_entity, edit_entity, view_entity_with_template, list_view

from tickets.models.ticket import Ticket
from tickets.forms.ticket import CreateForm, EditForm


@login_required
@get_view_or_die('tickets')
@add_view_or_die(ContentType.objects.get_for_model(Ticket), None, 'tickets')
def add(request):
    return add_entity(request, CreateForm)

def edit(request, ticket_id):
    return edit_entity(request, ticket_id, Ticket, EditForm, 'tickets')

@login_required
@get_view_or_die('tickets')
def detailview(request, ticket_id):
    return view_entity_with_template(request, ticket_id, Ticket,
                                     '/tickets/ticket',
                                     'tickets/view_ticket.html')

@login_required
@get_view_or_die('tickets')
def listview(request):
    return list_view(request, Ticket, extra_dict={'add_url':'/tickets/ticket/add'})
