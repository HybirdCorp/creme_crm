from unittest import skipIf

from creme.tickets import (
    get_ticket_model,
    get_tickettemplate_model,
    ticket_model_is_custom,
    tickettemplate_model_is_custom,
)

skip_ticket_tests = ticket_model_is_custom()
skip_tickettemplate_tests = tickettemplate_model_is_custom()

Ticket = get_ticket_model()
TicketTemplate = get_tickettemplate_model()


def skipIfCustomTicket(test_func):
    return skipIf(skip_ticket_tests, 'Custom Ticket model in use')(test_func)


def skipIfCustomTicketTemplate(test_func):
    return skipIf(skip_tickettemplate_tests, 'Custom TicketTemplate model in use')(test_func)
