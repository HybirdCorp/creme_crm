# -*- coding: utf-8 -*-

from .models import Ticket, TicketTemplate
from .forms.template import TicketTemplateRecurrentsForm


to_register = ((Ticket, TicketTemplate, TicketTemplateRecurrentsForm),
              )
