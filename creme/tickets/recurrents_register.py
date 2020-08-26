# -*- coding: utf-8 -*-

# from .forms.template import TicketTemplateRecurrentsForm
from . import custom_forms, get_ticket_model, get_tickettemplate_model

to_register = (
    # (get_ticket_model(), get_tickettemplate_model(), TicketTemplateRecurrentsForm),
    (
        get_ticket_model(),
        get_tickettemplate_model(),
        custom_forms.TTEMPLATE_CREATION_CFORM,
    ),
)
