# -*- coding: utf-8 -*-

from .models import Ticket, TicketTemplate
from .forms.template import TicketTemplateForm


to_register = ((Ticket, TicketTemplate, TicketTemplateForm),
              )
