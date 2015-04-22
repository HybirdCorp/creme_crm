# -*- coding: utf-8 -*-

from . import get_ticket_model, get_tickettemplate_model
#from .models import Ticket, TicketTemplate
from .forms.template import TicketTemplateRecurrentsForm


#to_register = ((Ticket, TicketTemplate, TicketTemplateRecurrentsForm),
to_register = ((get_ticket_model(), get_tickettemplate_model(), TicketTemplateRecurrentsForm),
              )
