# -*- coding: utf-8 -*-

from tickets.models import Ticket, TicketTemplate
from tickets.forms.template import TicketTemplateForm


to_register = ((Ticket, TicketTemplate, TicketTemplateForm),
              )
