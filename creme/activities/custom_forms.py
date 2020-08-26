# -*- coding: utf-8 -*-

from django.utils.translation import gettext_lazy as _

from creme import activities
from creme.activities.forms import activity
from creme.creme_core.gui.custom_form import CustomFormDescriptor

Activity = activities.get_activity_model()

ACTIVITY_CREATION_CFORM = CustomFormDescriptor(
    id='activities-activity_creation',
    model=Activity,
    verbose_name=_('Creation form for activity'),
    base_form_class=activity.BaseCreationCustomForm,
    excluded_fields=('start', 'end', 'type', 'sub_type'),
    extra_sub_cells=[
        activity.ActivitySubTypeSubCell(model=Activity),

        activity.NormalStartSubCell(model=Activity),
        activity.NormalEndSubCell(model=Activity),

        activity.MyParticipationSubCell(model=Activity),
        activity.ParticipatingUsersSubCell(model=Activity),
        activity.OtherParticipantsSubCell(model=Activity),
        activity.ActivitySubjectsSubCell(model=Activity),
        activity.LinkedEntitiesSubCell(model=Activity),

        activity.DatetimeAlertSubCell(model=Activity),
        activity.PeriodAlertSubCell(model=Activity),
        activity.UserMessagesSubCell(model=Activity),
    ],
)
ACTIVITY_CREATION_FROM_CALENDAR_CFORM = CustomFormDescriptor(
    id='activities-activity_creation_from_calendar',
    model=Activity,
    verbose_name=_('Creation form for activity from the Calendar'),
    base_form_class=activity.BaseCreationCustomForm,
    excluded_fields=[*ACTIVITY_CREATION_CFORM.excluded_fields],
    extra_sub_cells=[*ACTIVITY_CREATION_CFORM.extra_sub_cells],
)
UNAVAILABILITY_CREATION_FROM = CustomFormDescriptor(
    id='activities-unavailability_creation',
    model=Activity,
    verbose_name=_('Creation form for unavailability'),
    base_form_class=activity.BaseUnavailabilityCreationCustomForm,
    excluded_fields=[
        *ACTIVITY_CREATION_CFORM.excluded_fields,
        'busy',
    ],
    extra_sub_cells=[
        activity.UnavailabilityTypeSubCell(model=Activity),

        activity.UnavailabilityStartSubCell(model=Activity),
        activity.UnavailabilityEndSubCell(model=Activity),

        # activity.MyParticipationSubCell(model=Activity),
        activity.UnavailableUsersSubCell(model=Activity),
        # activity.OtherParticipantsSubCell(model=Activity),
        # activity.ActivitySubjectsSubCell(model=Activity),
        # activity.LinkedEntitiesSubCell(model=Activity),

        # activity.DatetimeAlertSubCell(model=Activity),
        # activity.PeriodAlertSubCell(model=Activity),
        # activity.UserMessagesSubCell(model=Activity),
    ],
)
ACTIVITY_EDITION_CFORM = CustomFormDescriptor(
    id='activities-activity_edition',
    model=Activity,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for activity'),
    base_form_class=activity.BaseEditionCustomForm,
    excluded_fields=('start', 'end', 'type', 'sub_type'),
    extra_sub_cells=[
        activity.ActivitySubTypeSubCell(model=Activity),
        activity.NormalStartSubCell(model=Activity),
        activity.NormalEndSubCell(model=Activity),
    ],
)

del Activity
