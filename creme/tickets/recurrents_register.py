# -*- coding: utf-8 -*-

from . import get_ticket_model, get_tickettemplate_model
from .forms.template import TicketTemplateRecurrentsForm


to_register = ((get_ticket_model(), get_tickettemplate_model(), TicketTemplateRecurrentsForm),
              )
