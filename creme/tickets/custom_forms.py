from django.utils.translation import gettext_lazy as _

from creme import tickets
from creme.creme_core.gui.custom_form import (
    CustomFormDefault,
    CustomFormDescriptor,
)

from .forms.template import BaseTemplateCustomForm

Ticket = tickets.get_ticket_model()
TicketTemplate = tickets.get_tickettemplate_model()


# ------------------------------------------------------------------------------
class TicketCreationFormDefault(CustomFormDefault):
    main_fields = ['user', 'title', 'priority', 'criticity', 'solution']


class TicketEditionFormDefault(CustomFormDefault):
    main_fields = ['user', 'title', 'status', 'priority', 'criticity', 'solution']


TICKET_CREATION_CFORM = CustomFormDescriptor(
    id='tickets-ticket_creation',
    model=Ticket,
    verbose_name=_('Creation form for ticket'),
    excluded_fields=('status',),
    default=TicketCreationFormDefault,
)
TICKET_EDITION_CFORM = CustomFormDescriptor(
    id='tickets-ticket_edition',
    model=Ticket,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for ticket'),
    default=TicketEditionFormDefault,
)


# ------------------------------------------------------------------------------
class TicketTemplateFormDefault(CustomFormDefault):
    main_fields = ['title', 'status', 'priority', 'criticity', 'solution']


TTEMPLATE_CREATION_CFORM = CustomFormDescriptor(
    id='tickets-template_creation',
    model=TicketTemplate,
    verbose_name=_('Creation form for ticket template'),
    base_form_class=BaseTemplateCustomForm,
    default=TicketTemplateFormDefault,
)
TTEMPLATE_EDITION_CFORM = CustomFormDescriptor(
    id='tickets-template_edition',
    model=TicketTemplate,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for ticket template'),
    base_form_class=BaseTemplateCustomForm,  # NB: not useful indeed
    default=TicketTemplateFormDefault,
)

del Ticket
del TicketTemplate
