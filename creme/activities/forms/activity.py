################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

import logging
from datetime import datetime, time, timedelta
from functools import partial

from django import forms
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils.timezone import localtime, make_aware
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

import creme.creme_core.forms as core_forms
from creme.creme_core.gui.custom_form import CustomFormExtraSubCell
from creme.creme_core.models import Relation, RelationType
from creme.creme_core.utils.chunktools import iter_as_chunk
from creme.persons import get_contact_model
from creme.persons.models import AbstractContact

from .. import constants, get_activity_model
from ..models import AbstractActivity, ActivitySubType, Calendar
from ..utils import check_activity_collisions, is_auto_orga_subject_enabled
from . import fields as act_fields
from .fields import (
    ActivitySubTypeField,
    DateWithOptionalTimeField,
    UserParticipationField,
)

logger = logging.getLogger(__name__)
Contact = get_contact_model()
Activity = get_activity_model()


# SUB-CELLS --------------------------------------------------------------------
class ActivitySubTypeSubCell(CustomFormExtraSubCell):
    sub_type_id = 'activities_subtype'
    verbose_name = _('Type')

    def formfield(self, instance, user, **kwargs):
        type_id = instance.type_id

        if type_id and (
            instance.pk is None
            or str(instance.type.uuid) == constants.UUID_TYPE_UNAVAILABILITY
        ):
            # TODO: improve help_text of end (we know the type default duration)
            limit_choices_to = Q(type_id=type_id)
        else:
            limit_choices_to = ~Q(type__uuid=constants.UUID_TYPE_UNAVAILABILITY)

        return ActivitySubTypeField(
            model=type(instance),
            field_name='sub_type',
            initial=instance.sub_type_id,
            user=user,
            label=self.verbose_name,
            required=True,
            limit_choices_to=limit_choices_to,
        )


class UnavailabilityTypeSubCell(CustomFormExtraSubCell):
    sub_type_id = 'activities_unavailability_subtype'
    verbose_name = _('Unavailability type')
    is_required = True

    def formfield(self, instance, user, **kwargs):
        return ActivitySubTypeField(
            model=type(instance),
            field_name='sub_type',
            initial=instance.sub_type_id,
            user=user,
            label=self.verbose_name,
            required=True,
            limit_choices_to=Q(type__uuid=constants.UUID_TYPE_UNAVAILABILITY),
        )


# -------------------------------------
class _ActivityDateSubCell(CustomFormExtraSubCell):
    attr_name = 'COMPLETE_ME'
    help_text = ''

    def formfield(self, instance, user, **kwargs):
        field = DateWithOptionalTimeField(
            label=self.verbose_name,
            help_text=self.help_text,
            **kwargs
        )

        dt = getattr(instance, self.attr_name, None)
        if dt:
            dt = localtime(dt)
            field.initial = (
                dt.date(),
                None
                if instance.floating_type == Activity.FloatingType.FLOATING_TIME else
                dt.time(),
            )

        return field


class StartSubCell(_ActivityDateSubCell):
    sub_type_id = 'activities_start'
    verbose_name = _('Start')
    attr_name = 'start'
    help_text = _(
        'You can specify:\n'
        ' - The date and the time (hour/minute).\n'
        ' - Only the date; the activity is placed in the calendar anyway '
        '(at the corresponding day).\n'
        ' - Neither the date neither the time; the activity is available in the '
        'calendar view in the panel «Floating activities».'
    )


# Same ID than StartSubCell to replace it transparently
class NormalStartSubCell(StartSubCell):
    is_required = False


# Idem
class UnavailabilityStartSubCell(StartSubCell):
    pass


class EndSubCell(_ActivityDateSubCell):
    sub_type_id = 'activities_end'
    verbose_name = _('End')
    attr_name = 'end'


# Same ID than EndSubCell to replace it transparently
class NormalEndSubCell(EndSubCell):
    sub_type_id = 'activities_end'
    verbose_name = _('End')
    is_required = False
    attr_name = 'end'

    def formfield(self, *args, **kwargs):
        field = super(EndSubCell, self).formfield(*args, **kwargs)
        field.help_text = _('Default duration of the type will be used if you leave blank.')

        return field


# Idem
class UnavailabilityEndSubCell(EndSubCell):
    pass


# -------------------------------------
class MyParticipationSubCell(CustomFormExtraSubCell):
    sub_type_id = 'activities_my_participation'
    verbose_name = _('Do I participate in this activity?')

    def formfield(self, instance, user, **kwargs):
        field = UserParticipationField(
            label=self.verbose_name, empty_label=None, user=user,
        )

        # TODO: if not instance.pk: ??
        if user.linked_contact:
            field.initial = (
                True,
                Calendar.objects.get_default_calendar(user).id,
            )

        return field


# -------------------------------------
class UsersSubCell(CustomFormExtraSubCell):
    sub_type_id = 'activities_users'
    verbose_name = 'Users'

    def formfield(self, instance, user, **kwargs):
        return act_fields.ParticipatingUsersField(
            label=self.verbose_name, user=user,
            **kwargs
        )


# Same ID than UsersSubCell to replace it transparently
class ParticipatingUsersSubCell(UsersSubCell):
    verbose_name = _('Other participating users')
    is_required = False

    def formfield(self, instance, user, **kwargs):
        field = super().formfield(instance=instance, user=user, **kwargs)
        field.queryset = field.queryset.exclude(pk=user.id)

        return field


# Idem
class UnavailableUsersSubCell(UsersSubCell):
    verbose_name = _('Unavailable users')


# -------------------------------------
class OtherParticipantsSubCell(CustomFormExtraSubCell):
    sub_type_id = 'activities_others_participants'
    verbose_name = _('Other participants')
    is_required = False

    def formfield(self, instance, user, **kwargs):
        return core_forms.MultiCreatorEntityField(
            label=self.verbose_name, model=Contact, user=user,
            q_filter={'is_user__isnull': True},
            # The creation view cannot create a Contact with a non-null 'is_user'.
            force_creation=True,
            **kwargs,
        )


class ActivitySubjectsSubCell(CustomFormExtraSubCell):
    sub_type_id = 'activities_subjects'
    verbose_name = _('Subjects')
    is_required = False

    def formfield(self, instance, user, **kwargs):
        return core_forms.MultiGenericEntityField(
            label=self.verbose_name, user=user,
            models=RelationType.objects.get(
                pk=constants.REL_SUB_ACTIVITY_SUBJECT,
            ).subject_models,
            help_text=_(
                'The organisations of the participants will be automatically added as subjects'
            ) if is_auto_orga_subject_enabled() else None,
            **kwargs
        )


class LinkedEntitiesSubCell(CustomFormExtraSubCell):
    sub_type_id = 'activities_linked'
    verbose_name = _('Entities linked to this activity')
    is_required = False

    relation_type_id = constants.REL_SUB_LINKED_2_ACTIVITY

    def formfield(self, instance, user, **kwargs):
        rtype = RelationType.objects.get(id=self.relation_type_id)

        if rtype.enabled:
            return core_forms.MultiGenericEntityField(
                label=self.verbose_name, user=user, autocomplete=True,
                **kwargs
            )
        else:
            return core_forms.ReadonlyMessageField(
                label=self.verbose_name, return_value=(),
                initial=gettext(
                    "The relationship type «{predicate}» is disabled; "
                    "re-enable it if it's still useful, "
                    "or remove this form-field in the forms configuration."
                ).format(predicate=rtype.predicate),
            )


# -------------------------------------
class _AssistantSubCell(CustomFormExtraSubCell):
    is_required = False

    def _concrete_formfield(self, instance, user, **kwargs):
        raise NotImplementedError

    @staticmethod
    def _create_alert(activity, trigger_date, **kwargs):
        from creme.assistants.models import Alert

        Alert.objects.create(
            user=activity.user,
            trigger_date=trigger_date,
            real_entity=activity,
            title=gettext('Alert of activity'),
            description=gettext('Alert related to {activity}').format(activity=activity),
            **kwargs
        )

    def formfield(self, instance, user, **kwargs):
        if apps.is_installed('creme.assistants'):
            field = self._concrete_formfield(
                instance=instance, user=user, label=self.verbose_name,
                **kwargs
            )
        else:
            field = core_forms.ReadonlyMessageField(
                label=self.verbose_name,
                initial=_(
                    'This field needs the app «Assistants» to be installed. '
                    'Hint: install it or remove this field in the form configuration.'
                ),
            )

        return field


class DatetimeAlertSubCell(_AssistantSubCell):
    sub_type_id = 'activities_alert_datetime'
    verbose_name = _('Generate an alert on a specific date')

    def _concrete_formfield(self, instance, user, **kwargs):
        return forms.DateTimeField(**kwargs)

    def post_save_instance(self, *, instance: AbstractActivity, value, form):
        if value:
            self._create_alert(instance, value)

        return False  # Do not save the Activity again (not modified)


class PeriodAlertSubCell(_AssistantSubCell):
    sub_type_id = 'activities_alert_period'
    verbose_name = _('Generate an alert in a while')

    error_messages = {
        'alert_on_floating': _(
            'You cannot set a relative alert on a floating activity'
        ),
    }

    def _concrete_formfield(self, instance, user, **kwargs):
        return core_forms.DatePeriodField(
            help_text=_(
                "How long before the activity's start the alert is raised?"
            ),
            period_names=('minutes', 'hours', 'days', 'weeks'),
            **kwargs,
        )

    def post_clean_instance(self, *, instance: AbstractActivity, value, form):
        if value and instance.floating_type == Activity.FloatingType.FLOATING:
            raise ValidationError(
                self.error_messages['alert_on_floating'],
                code='alert_on_floating',
            )

    def post_save_instance(self, *, instance: AbstractActivity, value, form):
        if value:
            self._create_alert(
                instance,
                trigger_date=instance.start - value.as_timedelta(),
                trigger_offset={
                    'cell': {'type': 'regular_field', 'value': 'start'},
                    'sign': -1,
                    'period': value.as_dict(),
                },
            )

        return False  # Do not save the Activity again (not modified)


class UserMessagesSubCell(_AssistantSubCell):
    sub_type_id = 'activities_user_messages'
    verbose_name = _('Users to keep informed')

    def _concrete_formfield(self, instance, user, **kwargs):
        return forms.ModelMultipleChoiceField(
            queryset=get_user_model().objects.filter(is_staff=False),
            **kwargs
        )

    def post_save_instance(self, *, instance: AbstractActivity, value, form):
        if value:
            from creme.assistants.constants import UUID_PRIORITY_NOT_IMPORTANT
            from creme.assistants.models import (
                UserMessage,
                UserMessagePriority,
            )

            title = gettext('[{software}] Activity created: {activity}').format(
                software=settings.SOFTWARE_LABEL,
                activity=instance,
            )
            body = gettext("""A new activity has been created: {activity}.
    Description: {description}.
    Start: {start}.
    End: {end}.
    Subjects: {subjects}.
    Participants: {participants}.""").format(
                activity=instance,
                description=instance.description,
                start=instance.start or gettext('not specified'),
                end=instance.end or gettext('not specified'),
                subjects=' / '.join(
                    str(e)
                    for e in form.cleaned_data.get(
                        form.subcell_key(ActivitySubjectsSubCell),
                        ()
                    )
                ),
                participants=' / '.join(str(c) for c in form.participants),
            )

            # TODO: sender = the real user that created the activity ???
            UserMessage.objects.create_for_users(
                users=value, title=title,
                body=body,
                priority=UserMessagePriority.objects.get(uuid=UUID_PRIORITY_NOT_IMPORTANT),
                sender=instance.user, entity=instance,
            )

        return False  # Do not save the Activity again (not modified)


# CUSTOM-FORMS -----------------------------------------------------------------
class BaseCustomForm(core_forms.CremeEntityForm):
    error_messages = {
        'floating_cannot_busy': _(
            "A floating on the day activity can't busy its participants"
        ),
        'no_start': _(
            "You can't set the end of your activity without setting its start"
        ),
        'end_before_start': _('End is before start'),
    }

    def clean(self):
        cdata = super().clean()

        if not self._errors:
            instance = self.instance
            instance.sub_type = self._get_activity_subtype()
            instance.type = instance.sub_type.type

            self._clean_temporal_data(activity_type=instance.type)

            start = instance.start
            if start:
                collisions = check_activity_collisions(
                    activity_start=start,
                    activity_end=instance.end,
                    participants=self._get_participants_2_check(),
                    # NB: fields should be always present,
                    #     so get() is here to prevent model's changes
                    busy=cdata.get('busy', False),
                    exclude_activity_id=self.instance.id,
                )
                if collisions:
                    raise ValidationError(collisions)

        return cdata

    def _clean_temporal_data(self, activity_type):
        instance = self.instance
        get_data = self.cleaned_data.get
        get_key = self.subcell_key
        start = end = None

        start_date_opt_time = get_data(get_key(StartSubCell))
        if start_date_opt_time:
            start_date = start_date_opt_time.date
            start_time = start_date_opt_time.time
        else:
            start_date = start_time = None

        end_date_opt_time = get_data(get_key(EndSubCell))
        if end_date_opt_time:
            end_date = end_date_opt_time.date
            end_time = end_date_opt_time.time
        else:
            end_date = end_time = None

        if not start_date:
            if end_date:
                raise ValidationError(self.error_messages['no_start'], code='no_start')

            floating_type = Activity.FloatingType.FLOATING
        else:
            is_all_day = get_data('is_all_day', False)

            floating_type = (
                Activity.FloatingType.NARROW
                if start_time or is_all_day else
                Activity.FloatingType.FLOATING_TIME
            )

            # TODO: not start_date, not end_date, start time, end time =>
            #       floating activity with time set but lost in the process

            if floating_type == Activity.FloatingType.FLOATING_TIME and get_data('busy', False):
                raise ValidationError(
                    self.error_messages['floating_cannot_busy'],
                    code='floating_cannot_busy',
                )

            start = make_aware(datetime.combine(start_date, start_time or time()))

            if end_date:
                end = make_aware(datetime.combine(end_date, end_time or time()))
            elif end_time is not None:
                end = make_aware(datetime.combine(start_date, end_time))
            else:
                tdelta = activity_type.as_timedelta()

                if (
                    is_all_day or floating_type == Activity.FloatingType.FLOATING_TIME
                ) and tdelta.days:
                    # In 'all day' mode, we round the number of day
                    # Activity already takes 1 day (we do not want it takes 2)
                    days = tdelta.days - 1

                    if tdelta.seconds:
                        days += 1

                    tdelta = timedelta(days=days)

                end = start + tdelta

            if is_all_day or floating_type == Activity.FloatingType.FLOATING_TIME:
                start = make_aware(datetime.combine(start, time(hour=0, minute=0)))
                end   = make_aware(datetime.combine(end,   time(hour=23, minute=59)))

            if start > end:
                raise ValidationError(
                    self.error_messages['end_before_start'],
                    code='end_before_start',
                )

        instance.start = start
        instance.end = end
        instance.floating_type = floating_type

    def _get_activity_subtype(self):
        return self.cleaned_data[self.subcell_key(ActivitySubTypeSubCell)]

    def _get_participants_2_check(self):
        return []


class BaseEditionCustomForm(BaseCustomForm):
    def _get_participants_2_check(self):
        return self.instance.get_related_entities(constants.REL_OBJ_PART_2_ACTIVITY)


class BaseCreationCustomForm(BaseCustomForm):
    error_messages = {
        **BaseCustomForm.error_messages,
        'no_participant': _('No participant'),
    }

    def __init__(self, sub_type: ActivitySubType | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # All Contacts who participate: me, other users, other contacts
        self.participants: set[AbstractContact] = set()
        self.calendars: list[Calendar] = []

        if sub_type:
            instance = self.instance
            instance.type_id = sub_type.type_id
            instance.sub_type = sub_type

    def clean(self):
        cdata = self.cleaned_data
        get_key = self.subcell_key
        participants = self.participants

        others_data = cdata.get(get_key(UsersSubCell))
        if others_data:
            participants.update(others_data['contacts'])
            self.calendars.extend(others_data['calendars'])

        my_participation = cdata.get(get_key(MyParticipationSubCell))
        if my_participation and my_participation.is_set:
            participants.add(self.user.linked_contact)
            self.calendars.append(my_participation.data)

        participants.update(cdata.get(get_key(OtherParticipantsSubCell), ()))

        if not participants:
            raise ValidationError(
                self.error_messages['no_participant'], code='no_participant',
            )

        return super().clean()

    def _get_relations_to_create(self):
        instance = self.instance
        cdata = self.cleaned_data

        get_key = self.subcell_key
        build_rel = partial(Relation, user=instance.user, object_entity=instance)

        return super()._get_relations_to_create().extend(
            build_rel(subject_entity_id=entity.id, type_id=rtype_id)
            for entities, rtype_id in (
                (self.participants, constants.REL_SUB_PART_2_ACTIVITY),
                (
                    cdata.get(get_key(ActivitySubjectsSubCell), ()),
                    constants.REL_SUB_ACTIVITY_SUBJECT,
                ),
                (
                    cdata.get(get_key(LinkedEntitiesSubCell), ()),
                    LinkedEntitiesSubCell.relation_type_id,
                ),
            )
            for entity in entities
        )

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)

        for calendars_chunk in iter_as_chunk(self.calendars, 256):
            instance.calendars.add(*calendars_chunk)

        return instance


class BaseUnavailabilityCreationCustomForm(BaseCreationCustomForm):
    class Meta(BaseCreationCustomForm.Meta):
        help_texts = {
            'is_all_day': _(
                'An unavailability always busies its participants; mark it as '
                '«all day» if you do not set the start/end times.'
            ),
        }

    def clean(self):
        self.cleaned_data['busy'] = True
        return super().clean()

    def _get_activity_subtype(self):
        return self.cleaned_data.get(self.subcell_key(UnavailabilityTypeSubCell))
