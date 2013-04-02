# -*- coding: utf-8 -*-

from creme.tickets.models import Ticket, TicketTemplate
from creme.tickets.forms.template import TicketTemplateForm


to_register = ((Ticket, TicketTemplate, TicketTemplateForm),
              )
