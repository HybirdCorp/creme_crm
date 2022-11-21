from django.utils.translation import gettext_lazy as _

from creme import events
from creme.creme_core.gui.custom_form import (
    CustomFormDefault,
    CustomFormDescriptor,
)

Event = events.get_event_model()


class EventFormDefault(CustomFormDefault):
    main_fields = [
        'user',
        'name',
        'type',
        'place',
        'start_date',
        'end_date',
        'budget',
        'final_cost',
    ]


EVENT_CREATION_CFORM = CustomFormDescriptor(
    id='events-event_creation',
    model=Event,
    verbose_name=_('Creation form for event'),
    default=EventFormDefault,
)
EVENT_EDITION_CFORM = CustomFormDescriptor(
    id='events-event_edition',
    model=Event,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for event'),
    default=EventFormDefault,
)

del Event
