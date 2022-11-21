from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

import creme.activities.forms.activity as activity_forms
from creme import activities
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.gui.custom_form import (
    LAYOUT_DUAL_SECOND,
    LAYOUT_REGULAR,
    CustomFormDefault,
    CustomFormDescriptor,
)

Activity = activities.get_activity_model()


class _ActivityCustomFormDefault(CustomFormDefault):
    sub_cells = {
        'sub_type': activity_forms.ActivitySubTypeSubCell,
        # 'is_comm_app': activity_forms.CommercialApproachSubCell,
    }

    def group_desc_for_when(self):
        model = self.descriptor.model

        return {
            'name': gettext('When'),
            'layout': LAYOUT_DUAL_SECOND,
            'cells': [
                activity_forms.StartSubCell(model=model).into_cell(),
                activity_forms.EndSubCell(model=model).into_cell(),
                (EntityCellRegularField, {'name': 'is_all_day'}),
            ],
        }


class ActivityCreationFormDefault(_ActivityCustomFormDefault):
    main_fields = [
        'user', 'title', 'minutes', 'place', 'duration', 'status', 'busy',
        'sub_type',
        # 'is_comm_app',
    ]

    def group_desc_for_participants(self):
        model = self.descriptor.model

        return {
            'name': gettext('Participants & subjects'),
            'cells': [
                activity_forms.MyParticipationSubCell(model=model).into_cell(),
                activity_forms.ParticipatingUsersSubCell(model=model).into_cell(),
                activity_forms.OtherParticipantsSubCell(model=model).into_cell(),
                activity_forms.ActivitySubjectsSubCell(model=model).into_cell(),
                activity_forms.LinkedEntitiesSubCell(model=model).into_cell(),
            ],
        }

    def group_desc_for_dt_alert(self):
        return {
            'name': gettext('Generate an alert on a specific date'),
            'layout': LAYOUT_DUAL_SECOND,
            'cells': [
                activity_forms.DatetimeAlertSubCell(model=self.descriptor.model).into_cell(),
            ],
        }

    def group_desc_for_period_alert(self):
        return {
            'name': gettext('Generate an alert in a while'),
            'layout': LAYOUT_DUAL_SECOND,
            'cells': [
                activity_forms.PeriodAlertSubCell(model=self.descriptor.model).into_cell(),
            ],
        }

    def groups_desc(self):
        return [
            self.group_desc_for_main_fields(),

            self.group_desc_for_when(),
            self.group_desc_for_dt_alert(),
            self.group_desc_for_period_alert(),

            self.group_desc_for_participants(),

            self.group_desc_for_description(layout=LAYOUT_REGULAR),
            self.group_desc_for_customfields(layout=LAYOUT_REGULAR),

            self.group_desc_for_properties(),
            self.group_desc_for_relations(),
            # {
            #     'name': gettext('Users to keep informed'),
            #     'cells': [
            #         activity_forms.UserMessagesSubCell(model=descriptor.model).into_cell(),
            #     ],
            # },
        ]


class ActivityFromCalendarFormDefault(ActivityCreationFormDefault):
    main_fields = [
        'user', 'title',
        # 'minutes',
        'place', 'duration', 'status', 'busy',
        'sub_type',
    ]

    # NB: <remaining=False> we do not want 'minutes' in the default form
    def group_desc_for_main_fields(self, remaining=False, **kwargs):
        return super().group_desc_for_main_fields(remaining=remaining, **kwargs)


class UnavailabilityCreationFormDefault(ActivityCreationFormDefault):
    sub_cells = {'sub_type': activity_forms.UnavailabilityTypeSubCell}
    main_fields = ['user', 'title', 'sub_type']

    def groups_desc(self):
        model = self.descriptor.model

        return [
            self.group_desc_for_main_fields(remaining=False),
            self.group_desc_for_when(),
            {
                'name': gettext('Unavailable users'),
                'cells': [
                    activity_forms.ParticipatingUsersSubCell(model=model).into_cell(),
                ],
            },

            self.group_desc_for_description(layout=LAYOUT_REGULAR),
            self.group_desc_for_customfields(layout=LAYOUT_REGULAR),

            self.group_desc_for_properties(),
            self.group_desc_for_relations(),
        ]


class ActivityEditionFormDefault(_ActivityCustomFormDefault):
    main_fields = [
        'user', 'title', 'minutes', 'place', 'duration', 'status', 'busy',
        'sub_type',
    ]

    def groups_desc(self):
        return [
            self.group_desc_for_main_fields(),
            self.group_desc_for_when(),
            self.group_desc_for_description(layout=LAYOUT_REGULAR),
            self.group_desc_for_customfields(layout=LAYOUT_REGULAR),
        ]


ACTIVITY_CREATION_CFORM = CustomFormDescriptor(
    id='activities-activity_creation',
    model=Activity,
    verbose_name=_('Creation form for activity'),
    base_form_class=activity_forms.BaseCreationCustomForm,
    excluded_fields=('start', 'end', 'type', 'sub_type'),
    extra_sub_cells=[
        activity_forms.ActivitySubTypeSubCell(model=Activity),

        activity_forms.NormalStartSubCell(model=Activity),
        activity_forms.NormalEndSubCell(model=Activity),

        activity_forms.MyParticipationSubCell(model=Activity),
        activity_forms.ParticipatingUsersSubCell(model=Activity),
        activity_forms.OtherParticipantsSubCell(model=Activity),
        activity_forms.ActivitySubjectsSubCell(model=Activity),
        activity_forms.LinkedEntitiesSubCell(model=Activity),

        activity_forms.DatetimeAlertSubCell(model=Activity),
        activity_forms.PeriodAlertSubCell(model=Activity),
        activity_forms.UserMessagesSubCell(model=Activity),
    ],
    default=ActivityCreationFormDefault,
)
ACTIVITY_CREATION_FROM_CALENDAR_CFORM = CustomFormDescriptor(
    id='activities-activity_creation_from_calendar',
    model=Activity,
    verbose_name=_('Creation form for activity from the Calendar'),
    base_form_class=activity_forms.BaseCreationCustomForm,
    excluded_fields=[*ACTIVITY_CREATION_CFORM.excluded_fields],
    extra_sub_cells=[*ACTIVITY_CREATION_CFORM.extra_sub_cells],
    default=ActivityFromCalendarFormDefault,
)
UNAVAILABILITY_CREATION_CFORM = CustomFormDescriptor(
    id='activities-unavailability_creation',
    model=Activity,
    verbose_name=_('Creation form for unavailability'),
    base_form_class=activity_forms.BaseUnavailabilityCreationCustomForm,
    excluded_fields=[
        *ACTIVITY_CREATION_CFORM.excluded_fields,
        'busy',
    ],
    extra_sub_cells=[
        activity_forms.UnavailabilityTypeSubCell(model=Activity),

        activity_forms.UnavailabilityStartSubCell(model=Activity),
        activity_forms.UnavailabilityEndSubCell(model=Activity),

        # activity_forms.MyParticipationSubCell(model=Activity),
        activity_forms.UnavailableUsersSubCell(model=Activity),
        # activity_forms.OtherParticipantsSubCell(model=Activity),
        # activity_forms.ActivitySubjectsSubCell(model=Activity),
        # activity_forms.LinkedEntitiesSubCell(model=Activity),

        # activity_forms.DatetimeAlertSubCell(model=Activity),
        # activity_forms.PeriodAlertSubCell(model=Activity),
        # activity_forms.UserMessagesSubCell(model=Activity),
    ],
    default=UnavailabilityCreationFormDefault,
)
ACTIVITY_EDITION_CFORM = CustomFormDescriptor(
    id='activities-activity_edition',
    model=Activity,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for activity'),
    base_form_class=activity_forms.BaseEditionCustomForm,
    excluded_fields=('start', 'end', 'type', 'sub_type'),
    extra_sub_cells=[
        activity_forms.ActivitySubTypeSubCell(model=Activity),
        activity_forms.NormalStartSubCell(model=Activity),
        activity_forms.NormalEndSubCell(model=Activity),
    ],
    default=ActivityEditionFormDefault,
)

del Activity
