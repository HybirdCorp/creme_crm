# -*- coding: utf-8 -*-

from django.utils.translation import gettext_lazy as _

from creme import tickets
from creme.creme_core.gui.custom_form import CustomFormDescriptor

from .forms.template import BaseTemplateCustomForm

Ticket = tickets.get_ticket_model()
TicketTemplate = tickets.get_tickettemplate_model()


TICKET_CREATION_CFORM = CustomFormDescriptor(
    id='tickets-ticket_creation',
    model=Ticket,
    verbose_name=_('Creation form for ticket'),
    excluded_fields=('status',),
)
TICKET_EDITION_CFORM = CustomFormDescriptor(
    id='tickets-ticket_edition',
    model=Ticket,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for ticket'),
)

TTEMPLATE_CREATION_CFORM = CustomFormDescriptor(
    id='tickets-template_creation',
    model=TicketTemplate,
    verbose_name=_('Creation form for ticket template'),
    base_form_class=BaseTemplateCustomForm,
)
TTEMPLATE_EDITION_CFORM = CustomFormDescriptor(
    id='tickets-template_edition',
    model=TicketTemplate,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for ticket template'),
    base_form_class=BaseTemplateCustomForm,  # NB: not useful indeed
)

del Ticket
del TicketTemplate
