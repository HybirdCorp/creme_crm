# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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
# import warnings
from datetime import datetime, time, timedelta
from functools import partial

from django import forms
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.timezone import localtime
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core import forms as core_forms
# from creme.creme_core.forms import widgets as core_widgets
from creme.creme_core.gui.custom_form import CustomFormExtraSubCell
from creme.creme_core.models import Relation, RelationType  # SettingValue
from creme.creme_core.utils.chunktools import iter_as_chunk
from creme.creme_core.utils.dates import make_aware_dt
from creme.persons import get_contact_model

from .. import constants, get_activity_model
from ..models import AbstractActivity, ActivitySubType, ActivityType, Calendar
# from ..setting_keys import form_user_messages_key
from ..utils import check_activity_collisions, is_auto_orga_subject_enabled
from . import fields as act_fields
from .activity_type import ActivityTypeField
from .fields import DateWithOptionalTimeField, UserParticipationField

logger = logging.getLogger(__name__)
Contact = get_contact_model()
Activity = get_activity_model()


# SUB-CELLS --------------------------------------------------------------------
class ActivitySubTypeSubCell(CustomFormExtraSubCell):
    sub_type_id = 'activities_subtype'
    verbose_name = _('Type')

    def formfield(self, instance, user, **kwargs):
        type_id = instance.type_id
        if type_id and (instance.pk is None or type_id == constants.ACTIVITYTYPE_INDISPO):
            # TODO: improve help_text of end (we know the type default duration)
            types = ActivityType.objects.filter(pk=type_id)
        else:
            types = ActivityType.objects.exclude(pk=constants.ACTIVITYTYPE_INDISPO)

        return ActivityTypeField(
            label=self.verbose_name,
            initial=(instance.type_id, instance.sub_type_id),
            user=user,
            types=types,
        )


class UnavailabilityTypeSubCell(CustomFormExtraSubCell):
    sub_type_id = 'activities_unavailability_subtype'
    verbose_name = _('Unavailability type')
    is_required = False

    def formfield(self, instance, user, **kwargs):
        return forms.ModelChoiceField(
            label=self.verbose_name,
            queryset=ActivitySubType.objects.filter(type=constants.ACTIVITYTYPE_INDISPO),
            **kwargs
        )


# -------------------------------------
class _ActivityDateSubCell(CustomFormExtraSubCell):
    attr_name = 'COMPLETE_ME'

    def formfield(self, instance, user, **kwargs):
        field = DateWithOptionalTimeField(label=self.verbose_name, **kwargs)

        dt = getattr(instance, self.attr_name, None)
        if dt:
            dt = localtime(dt)
            field.initial = (
                dt.date(),
                None if instance.floating_type == constants.FLOATING_TIME else dt.time(),
            )

        return field


class StartSubCell(_ActivityDateSubCell):
    sub_type_id = 'activities_start'
    verbose_name = _('Start')
    attr_name = 'start'


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
    verbose_name = _('Do I participate to this activity?')

    def formfield(self, instance, user, **kwargs):
        field = UserParticipationField(
            label=self.verbose_name, empty_label=None, user=user,
        )

        # TODO: if not instance.pk: ??
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
            models=[
                ct.model_class()
                for ct in RelationType.objects
                                      .get(pk=constants.REL_SUB_ACTIVITY_SUBJECT)
                                      .subject_ctypes.all()
            ],
            help_text=_(
                'The organisations of the participants will be automatically added as subjects'
            ) if is_auto_orga_subject_enabled() else None,
            **kwargs
        )


class LinkedEntitiesSubCell(CustomFormExtraSubCell):
    sub_type_id = 'activities_linked'
    verbose_name = _('Entities linked to this activity')
    is_required = False

    def formfield(self, instance, user, **kwargs):
        return core_forms.MultiGenericEntityField(
            label=self.verbose_name, user=user, autocomplete=True,
            **kwargs
        )


# -------------------------------------
class _AssistantSubCell(CustomFormExtraSubCell):
    is_required = False

    def _concrete_formfield(self, instance, user, **kwargs):
        raise NotImplementedError()

    @staticmethod
    def _create_alert(activity, trigger_date):
        from creme.assistants.models import Alert

        Alert.objects.create(
            user=activity.user,
            trigger_date=trigger_date,
            creme_entity=activity,
            title=gettext('Alert of activity'),
            description=gettext('Alert related to {activity}').format(activity=activity),
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
        if value and instance.floating_type == constants.FLOATING:
            raise ValidationError(
                self.error_messages['alert_on_floating'],
                code='alert_on_floating',
            )

    def post_save_instance(self, *, instance: AbstractActivity, value, form):
        if value:
            self._create_alert(instance, instance.start - value.as_timedelta())

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
            from creme.assistants.constants import PRIO_NOT_IMP_PK
            from creme.assistants.models import UserMessage

            title = gettext('[Creme] Activity created: {activity}').format(activity=instance)
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
            UserMessage.create_messages(
                users=value, title=title,
                body=body, priority_id=PRIO_NOT_IMP_PK,
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
            instance.type, instance.sub_type = self._get_activity_type_n_subtype()

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

        start_date, start_time = get_data(get_key(StartSubCell)) or (None, None)
        end_date,   end_time   = get_data(get_key(EndSubCell))   or (None, None)

        if not start_date:
            if end_date:
                raise ValidationError(self.error_messages['no_start'], code='no_start')

            floating_type = constants.FLOATING
        else:
            is_all_day = get_data('is_all_day', False)

            floating_type = (
                constants.NARROW
                if start_time or end_time or is_all_day else
                constants.FLOATING_TIME
            )

            # TODO: not start_date, not end_date, start time, end time =>
            #       floating activity with time set but lost in the process

            if floating_type == constants.FLOATING_TIME and get_data('busy', False):
                raise ValidationError(
                    self.error_messages['floating_cannot_busy'],
                    code='floating_cannot_busy',
                )

            start = make_aware_dt(datetime.combine(start_date, start_time or time()))

            if end_date:
                end = make_aware_dt(datetime.combine(end_date, end_time or time()))
            elif end_time is not None:
                end = make_aware_dt(datetime.combine(start_date, end_time))
            else:
                tdelta = activity_type.as_timedelta()

                if (is_all_day or floating_type == constants.FLOATING_TIME) and tdelta.days:
                    # In 'all day' mode, we round the number of day
                    # Activity already takes 1 day (we do not want it takes 2)
                    days = tdelta.days - 1

                    if tdelta.seconds:
                        days += 1

                    tdelta = timedelta(days=days)

                end = start + tdelta

            if is_all_day or floating_type == constants.FLOATING_TIME:
                start = make_aware_dt(datetime.combine(start, time(hour=0, minute=0)))
                end   = make_aware_dt(datetime.combine(end,   time(hour=23, minute=59)))

            if start > end:
                raise ValidationError(
                    self.error_messages['end_before_start'],
                    code='end_before_start',
                )

        instance.start = start
        instance.end = end
        instance.floating_type = floating_type

    def _get_activity_type_n_subtype(self):
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

    def __init__(self, activity_type_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # All Contacts who participate: me, other users, other contacts
        self.participants = set()

        if activity_type_id:
            self.instance.type_id = activity_type_id

    def clean(self):
        cdata = self.cleaned_data
        get_key = self.subcell_key
        participants = self.participants

        participants.update(cdata.get(get_key(UsersSubCell), ()))

        my_participation = cdata.get(get_key(MyParticipationSubCell))
        if my_participation and my_participation[0]:
            participants.add(self.user.linked_contact)

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
                    constants.REL_SUB_LINKED_2_ACTIVITY,
                ),
            )
            for entity in entities
        )

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)
        cdata = self.cleaned_data
        get_key = self.subcell_key
        calendars = [
            *Calendar.objects.get_default_calendars(
                part_user.is_user
                for part_user in cdata.get(get_key(UsersSubCell), ())
            ).values()
        ]

        i_participate, my_calendar = cdata.get(
            get_key(MyParticipationSubCell), (False, None)
        )
        if i_participate:
            calendars.append(my_calendar)

        for calendars_chunk in iter_as_chunk(calendars, 256):
            instance.calendars.add(*calendars_chunk)

        return instance


class BaseUnavailabilityCreationCustomForm(BaseCreationCustomForm):
    class Meta(BaseCreationCustomForm.Meta):
        help_texts = {
            'is_all_day': _(
                'An unavailability always busies its participants ; mark it as '
                '«all day» if you do not set the start/end times.'
            ),
        }

    def clean(self):
        self.cleaned_data['busy'] = True
        return super().clean()

    def _get_activity_type_n_subtype(self):
        return (
            ActivityType.objects.get(pk=constants.ACTIVITYTYPE_INDISPO),
            self.cleaned_data.get(self.subcell_key(UnavailabilityTypeSubCell)),
        )


# OLD FORMS --------------------------------------------------------------------
# class _ActivityForm(core_forms.CremeEntityForm):
#     type_selector = ActivityTypeField(
#         label=_('Type'),
#         types=ActivityType.objects.exclude(pk=constants.ACTIVITYTYPE_INDISPO),
#     )
#
#     start_time = forms.TimeField(label=_('Start time'), required=False)
#     end_time   = forms.TimeField(label=_('End time'), required=False)
#
#     error_messages = {
#         'floating_cannot_busy': _("A floating on the day activity can't busy its participants"),
#         'no_start': _("You can't set the end of your activity without setting its start"),
#         'end_before_start_time': _('End time is before start time'),
#     }
#
#     class Meta(core_forms.CremeEntityForm.Meta):
#         model = Activity
#         exclude = (*core_forms.CremeEntityForm.Meta.exclude, 'type', 'sub_type')
#         widgets = {
#             'start': core_widgets.CalendarWidget,
#             'end': core_widgets.CalendarWidget,
#         }
#         help_texts = {
#             'end': _('Default duration of the type will be used if you leave blank.'),
#         }
#
#     def __init__(self, *args, **kwargs):
#         warnings.warn('_ActivityForm is deprecated.', DeprecationWarning)
#         super().__init__(*args, **kwargs)
#         self.participants = set()
#
#     def clean(self):
#         cdata = super().clean()
#
#         if not self._errors:
#             self.floating_type = self._clean_interval(self._get_activity_type_n_subtype()[0])
#
#             start = cdata['start']
#             if start:
#                 collisions = check_activity_collisions(start, cdata['end'],
#                                                        self._get_participants_2_check(),
#                                                        busy=cdata['busy'],
#                                                        exclude_activity_id=self.instance.pk,
#                                                       )
#                 if collisions:
#                     raise ValidationError(collisions)
#
#         return cdata
#
#     def _clean_interval(self, atype):
#         cdata = self.cleaned_data
#         start = cdata['start']
#         end   = cdata['end']
#
#         if not start and not end:
#             return constants.FLOATING
#
#         floating_type = constants.NARROW
#
#         get = cdata.get
#         is_all_day = get('is_all_day', False)
#         start_time = get('start_time')
#         end_time   = get('end_time')
#
#         # TODO: not start, not end, start time, end time =>
#         #       floating activity with time set but lost in the process
#
#         if start_time is None and end_time is None:
#             if not is_all_day:
#                 if get('busy', False):
#                     raise ValidationError(self.error_messages['floating_cannot_busy'],
#                                           code='floating_cannot_busy',
#                                          )
#
#                 floating_type = constants.FLOATING_TIME
#
#         if not start and end:
#             raise ValidationError(self.error_messages['no_start'], code='no_start')
#
#         if start and start_time:
#             start = make_aware_dt(datetime.combine(start, start_time))
#
#         if end and end_time:
#             end = make_aware_dt(datetime.combine(end, end_time))
#
#         if start and not end:
#             if end_time is not None:
#                 end = make_aware_dt(datetime.combine(start, end_time))
#             else:
#                 tdelta = atype.as_timedelta()
#
#                 if (is_all_day or floating_type == constants.FLOATING_TIME) and tdelta.days:
#                     # In 'all day' mode, we round the number of day
#                     # Activity already takes 1 day (we do not want it takes 2)
#                     days = tdelta.days - 1
#
#                     if tdelta.seconds:
#                         days += 1
#
#                     tdelta = timedelta(days=days)
#
#                 end = start + tdelta
#
#         if is_all_day or floating_type == constants.FLOATING_TIME:
#             start = make_aware_dt(datetime.combine(start, time(hour=0, minute=0)))
#             end   = make_aware_dt(datetime.combine(end, time(hour=23, minute=59)))
#
#         if start > end:
#             raise ValidationError(self.error_messages['end_before_start_time'],
#                                   code='end_before_start_time',
#                                  )
#
#         cdata['start'] = start
#         cdata['end'] = end
#
#         return floating_type
#
#     def _get_activity_type_n_subtype(self):
#         return self.cleaned_data['type_selector']
#
#     def _get_participants_2_check(self):
#         return self.participants
#
#     def _get_relations_to_create(self):
#         instance = self.instance
#         build_rel = partial(Relation, user=instance.user, object_entity=instance,
#                             type_id=constants.REL_SUB_PART_2_ACTIVITY
#                            )
#
#         return super()._get_relations_to_create().extend(
#             build_rel(subject_entity=p) for p in self.participants
#         )
#
#     def save(self, *args, **kwargs):
#         instance = self.instance
#         instance.floating_type = self.floating_type
#         instance.type, instance.sub_type = self._get_activity_type_n_subtype()
#
#         return super().save(*args, **kwargs)


# class ActivityEditForm(_ActivityForm):
#     blocks = _ActivityForm.blocks.new(
#         ('datetime', _('When'), ['is_all_day', 'start', 'start_time', 'end', 'end_time']),
#     )
#
#     @staticmethod
#     def _localize(dt):
#         return localtime(dt) if dt else dt
#
#     def __init__(self, *args, **kwargs):
#         warnings.warn('ActivityEditForm is deprecated.', DeprecationWarning)
#         super().__init__(*args, **kwargs)
#         fields = self.fields
#         instance = self.instance
#
#         type_f = fields['type_selector']
#         type_f.initial = (instance.type_id, instance.sub_type_id)
#
#         if self.instance.type_id == constants.ACTIVITYTYPE_INDISPO:
#             type_f.types = ActivityType.objects.filter(pk=constants.ACTIVITYTYPE_INDISPO)
#
#         if instance.floating_type == constants.NARROW:
#             start = self._localize(instance.start)
#             if start:
#                 fields['start_time'].initial = start.time()
#
#             end = self._localize(instance.end)
#             if end:
#                 fields['end_time'].initial = end.time()
#
#     def _get_participants_2_check(self):
#         return self.instance.get_related_entities(constants.REL_OBJ_PART_2_ACTIVITY)


# class _ActivityCreateForm(_ActivityForm):
#     participating_users = act_fields.ParticipatingUsersField(
#         label=_('Other participating users'),
#         required=False,
#     )
#
#     def __init__(self, *args, **kwargs):
#         warnings.warn('_ActivityCreateForm is deprecated.', DeprecationWarning)
#         super().__init__(*args, **kwargs)
#
#     def clean_participating_users(self):
#         user_contacts = self.cleaned_data['participating_users']
#         self.participants.update(user_contacts)
#
#         return {contact.is_user for contact in user_contacts}
#
#     def save(self, *args, **kwargs):
#         instance = super().save(*args, **kwargs)
#
#         for part_user in self.cleaned_data['participating_users']:
#             instance.calendars.add(Calendar.objects.get_default_calendar(part_user))
#
#         return instance


# class ActivityCreateForm(_ActivityCreateForm):
#     my_participation = act_fields.UserParticipationField(
#         label=_('Do I participate to this activity?'), empty_label=None,
#     )
#
#     other_participants = core_forms.MultiCreatorEntityField(
#         label=_('Other participants'), model=Contact, required=False,
#     )
#     subjects = core_forms.MultiGenericEntityField(
#         label=_('Subjects'), required=False,
#     )
#     linked_entities = core_forms.MultiGenericEntityField(
#         label=_('Entities linked to this activity'), required=False,
#     )
#
#     error_messages = {
#         **_ActivityCreateForm.error_messages,
#         'no_participant': _('No participant'),
#         'alert_on_floating': _('You cannot set a relative alert on a floating activity'),
#     }
#
#     blocks = _ActivityForm.blocks.new(
#         (
#             'datetime', _('When'),
#             ['start', 'start_time', 'end', 'end_time', 'is_all_day'],
#         ),
#         (
#             'participants', _('Participants & subjects'),
#             ['my_participation', 'participating_users', 'other_participants',
#              'subjects', 'linked_entities',
#             ],
#         ),
#         ('alert_datetime', _('Generate an alert on a specific date'), ['alert_start']),
#         ('alert_period',   _('Generate an alert in a while'),         ['alert_period']),
#         ('informed_users', _('Users to keep informed'),               ['informed_users']),
#     )
#
#     def __init__(self, activity_type_id=None, *args, **kwargs):
#         warnings.warn('ActivityCreateForm is deprecated.', DeprecationWarning)
#         super().__init__(*args, **kwargs)
#         user   = self.user
#         fields = self.fields
#
#         if activity_type_id:
#             fields['type_selector'].types = ActivityType.objects.filter(pk=activity_type_id)
#
#         fields['my_participation'].initial = (
#             True,
#             Calendar.objects.get_default_calendar(user).id,
#         )
#
#         subjects_field = fields['subjects']
#         subjects_field.allowed_models = [
#             ct.model_class()
#             for ct in RelationType.objects
#                                   .get(pk=constants.REL_SUB_ACTIVITY_SUBJECT)
#                                   .subject_ctypes.all()
#         ]
#         if is_auto_orga_subject_enabled():
#             subjects_field.help_text = _(
#                 'The organisations of the participants will be automatically added as subjects'
#             )
#
#         part_users_f = fields['participating_users']
#         part_users_f.queryset = part_users_f.queryset.exclude(pk=user.id)
#
#         other_f = fields['other_participants']
#         other_f.q_filter = {'is_user__isnull': True}
#         # The creation view cannot create a Contact with a non-null 'is_user'.
#         other_f.force_creation = True  # TODO: in constructor
#
#         if apps.is_installed('creme.assistants'):
#             self._add_specified_alert_fields(fields)
#             self._add_duration_alert_fields(fields)
#             self._add_informed_users_fields(fields)
#
#     @staticmethod
#     def _add_specified_alert_fields(fields):
#         fields['alert_start'] = forms.DateTimeField(
#             label=_('Generate an alert on a specific date'), required=False,
#         )
#
#     @staticmethod
#     def _add_duration_alert_fields(fields):
#         fields['alert_period'] = core_forms.DatePeriodField(
#             label=_('Generate an alert in a while'),
#             required=False,
#             help_text=_("How long before the activity's start the alert is raised?"),
#             period_names=('minutes', 'hours', 'days', 'weeks'),
#         )
#
#     @staticmethod
#     def _add_informed_users_fields(fields):
#         if SettingValue.objects.get_4_key(form_user_messages_key, default=False).value:
#             fields['informed_users'] = forms.ModelMultipleChoiceField(
#                 queryset=get_user_model().objects.filter(is_staff=False),
#                 required=False,
#                 label=_('Users to keep informed'),
#             )
#
#     def clean_alert_period(self):
#         cdata = self.cleaned_data
#         alert_period = cdata['alert_period']
#
#         if alert_period and not cdata.get('start'):
#             raise ValidationError(
#                 self.error_messages['alert_on_floating'], code='alert_on_floating',
#             )
#
#         return alert_period
#
#     def clean_my_participation(self):
#         my_participation = self.cleaned_data['my_participation']
#
#         if my_participation[0]:
#             self.participants.add(self.user.linked_contact)
#
#         return my_participation
#
#     def clean_other_participants(self):
#         participants = self.cleaned_data['other_participants']
#         self.participants.update(participants)
#         return participants
#
#     def clean(self):
#         if not self._errors:
#             cdata = self.cleaned_data
#
#             if not cdata['my_participation'][0] and not cdata['participating_users']:
#                 raise ValidationError(
#                     self.error_messages['no_participant'], code='no_participant',
#                 )
#
#         return super().clean()
#
#     def _get_relations_to_create(self):
#         instance = self.instance
#         cdata = self.cleaned_data
#         build_rel = partial(Relation, object_entity=instance, user=instance.user)
#
#         return super()._get_relations_to_create().extend(
#             build_rel(subject_entity_id=entity.id, type_id=rtype_id)
#             for entities, rtype_id in (
#                 (cdata['subjects'],        constants.REL_SUB_ACTIVITY_SUBJECT),
#                 (cdata['linked_entities'], constants.REL_SUB_LINKED_2_ACTIVITY),
#             )
#             for entity in entities
#         )
#
#     def save(self, *args, **kwargs):
#         instance = super().save(*args, **kwargs)
#
#         self._generate_alerts()
#         self._generate_user_messages()
#
#         i_participate, my_calendar = self.cleaned_data['my_participation']
#         if i_participate:
#             instance.calendars.add(my_calendar)
#
#         return instance
#
#     @staticmethod
#     def _create_alert(activity, trigger_date):
#         from creme.assistants.models import Alert
#
#         Alert.objects.create(
#             user=activity.user,
#             trigger_date=trigger_date,
#             creme_entity=activity,
#             title=gettext('Alert of activity'),
#             description=gettext('Alert related to {activity}').format(activity=activity),
#         )
#
#     def _generate_alerts(self):
#         get = self.cleaned_data.get
#         activity = self.instance
#         alert_start = get('alert_start')
#
#         if alert_start:
#             self._create_alert(activity, alert_start)
#
#         period = get('alert_period')
#         if period:
#             self._create_alert(activity, activity.start - period.as_timedelta())
#
#     def _generate_user_messages(self):
#         cdata = self.cleaned_data
#         raw_users = cdata.get('informed_users')
#
#         if raw_users:
#             from creme.assistants.constants import PRIO_NOT_IMP_PK
#             from creme.assistants.models import UserMessage
#
#             activity = self.instance
#             title = gettext('[Creme] Activity created: {activity}').format(activity=activity)
#             body = gettext("""A new activity has been created: {activity}.
#     Description: {description}.
#     Start: {start}.
#     End: {end}.
#     Subjects: {subjects}.
#     Participants: {participants}.""").format(
#                 activity=activity,
#                 description=activity.description,
#                 start=activity.start or gettext('not specified'),
#                 end=activity.end or gettext('not specified'),
#                 subjects=' / '.join(str(e) for e in cdata['subjects']),
#                 participants=' / '.join(str(c) for c in self.participants),
#             )
#
#             UserMessage.create_messages(
#                 users=raw_users, title=title,
#                 body=body, priority_id=PRIO_NOT_IMP_PK,
#                 sender=activity.user, entity=activity,
#             )


# class RelatedActivityCreateForm(ActivityCreateForm):
#     def __init__(self, related_entity, relation_type_id, *args, **kwargs):
#         warnings.warn('RelatedActivityCreateForm is deprecated.', DeprecationWarning)
#
#         super().__init__(*args, **kwargs)
#
#         if relation_type_id == constants.REL_SUB_PART_2_ACTIVITY:
#             assert isinstance(related_entity, Contact)
#
#             if related_entity.is_user:
#                 self.fields['participating_users'].initial = [related_entity.is_user]
#             else:
#                 self.fields['other_participants'].initial = [related_entity]
#         elif relation_type_id == constants.REL_SUB_ACTIVITY_SUBJECT:
#             self.fields['subjects'].initial = [related_entity]
#         else:
#             assert relation_type_id == constants.REL_SUB_LINKED_2_ACTIVITY
#             self.fields['linked_entities'].initial = [related_entity]


# class CalendarActivityCreateForm(ActivityCreateForm):
#     class Meta(ActivityCreateForm.Meta):
#         exclude = (*ActivityCreateForm.Meta.exclude, 'minutes')
#
#     def __init__(self, *args, **kwargs):
#         warnings.warn('CalendarActivityCreateForm is deprecated.', DeprecationWarning)
#         super().__init__(*args, **kwargs)


# class IndisponibilityCreateForm(_ActivityCreateForm):
#     type_selector = forms.ModelChoiceField(
#         label=_('Unavailability type'), required=False,
#         queryset=ActivitySubType.objects.filter(type=constants.ACTIVITYTYPE_INDISPO),
#     )
#
#     class Meta(_ActivityCreateForm.Meta):
#         exclude = (
#             *_ActivityCreateForm.Meta.exclude,
#             'place', 'description', 'minutes', 'busy', 'status',
#             'duration',
#         )  # TODO: test
#         help_texts = {
#             'is_all_day': _(
#                 'An unavailability always busies its participants ; mark it as '
#                 '«all day» if you do not set the start/end times.'
#             ),
#         }
#
#     blocks = _ActivityCreateForm.blocks.new(
#         (
#             'datetime',
#             _('When'),
#             ['is_all_day', 'start', 'start_time', 'end', 'end_time'],
#         ),
#         ('participants', _('Participants'), ['participating_users']),
#     )
#
#     def __init__(self, activity_type_id=None, *args, **kwargs):
#         warnings.warn('IndisponibilityCreateForm is deprecated.', DeprecationWarning)
#
#         assert activity_type_id == constants.ACTIVITYTYPE_INDISPO
#         super().__init__(*args, **kwargs)
#         fields = self.fields
#
#         fields['start'].required = True
#
#         end_f = fields['end']
#         end_f.required = True
#         end_f.help_text = None
#
#         p_users_field = fields['participating_users']
#         p_users_field.label = _('Unavailable users')
#         p_users_field.required = True
#
#     def clean(self):
#         self.cleaned_data['busy'] = True
#         return super().clean()
#
#     def _get_activity_type_n_subtype(self):
#         return (
#             ActivityType.objects.get(pk=constants.ACTIVITYTYPE_INDISPO),
#             self.cleaned_data['type_selector'],
#         )
