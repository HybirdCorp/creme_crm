# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from functools import partial
from datetime import datetime, time, timedelta
from logging import warn

from django.forms import IntegerField, BooleanField, ModelChoiceField, ModelMultipleChoiceField
from django.forms.fields import ChoiceField, DateTimeField
from django.forms.util import ValidationError, ErrorList
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.auth.models import User

from creme_core.models import Relation
from creme_core.forms import CremeForm, CremeEntityForm
from creme_core.forms.base import FieldBlockManager
from creme_core.forms.fields import CremeDateTimeField, CremeTimeField, MultiCremeEntityField, MultiGenericEntityField
from creme_core.forms.widgets import UnorderedMultipleChoiceWidget
from creme_core.forms.validators import validate_linkable_entities, validate_linkable_entity

from creme_config.forms.fields import CreatorModelChoiceField

from persons.models import Contact

from assistants.models.alert import Alert

from activities.models import ActivityType, Activity, PhoneCall, Meeting, Calendar
from activities.constants import *
from activities.utils import check_activity_collisions


MINUTE  = '1'
HOUR    = '2'
DAY     = '3'
WEEK    = '4'
UNITY_TAB = [(MINUTE, _(u'Minute')), (HOUR, _(u'Hour')), (DAY, _(u'Day',)), (WEEK, _(u'Week'))]

def _clean_interval(cleaned_data):
    if cleaned_data.get('is_all_day'):
        cleaned_data['start_time'] = time(hour=0,  minute=0)
        cleaned_data['end_time']   = time(hour=23, minute=59)

    start_time = cleaned_data.get('start_time') or time()
    end_time   = cleaned_data.get('end_time') or time()

    cleaned_data['start'] = cleaned_data['start'].replace(hour=start_time.hour, minute=start_time.minute)

    if not cleaned_data.get('end'):
        cleaned_data['end'] = cleaned_data['start']

    cleaned_data['end'] = cleaned_data['end'].replace(hour=end_time.hour, minute=end_time.minute)

    if cleaned_data['start'] > cleaned_data['end']:
        raise ValidationError(ugettext(u"End time is before start time"))

def _check_activity_collisions(activity_start, activity_end, participants, busy=True, exclude_activity_id=None):
    collisions = check_activity_collisions(activity_start, activity_end, participants, busy=busy, exclude_activity_id=exclude_activity_id)
    if collisions:
        raise ValidationError(collisions)

#TODO: factorise with ActivityCreateForm !!
class ParticipantCreateForm(CremeForm):
    my_participation    = BooleanField(required=False, label=_(u"Do I participate to this meeting ?"),initial=False)
    my_calendar         = ModelChoiceField(queryset=Calendar.objects.none(), required=False, empty_label=None,
                                           label=_(u"On which of my calendar this activity will appears?"))
    participating_users = ModelMultipleChoiceField(label=_(u'Other participating users'), queryset=User.objects.all(),
                                                   required=False, widget=UnorderedMultipleChoiceWidget)
    participants        = MultiCremeEntityField(label=_(u'Participants'), model=Contact, required=False)

    def __init__(self, entity, *args, **kwargs):
        super(ParticipantCreateForm, self).__init__(*args, **kwargs)

        self.activity = entity
        self.participants = []

        user = self.user
        user_pk = user.pk
        fields = self.fields

        existing = Contact.objects.filter(relations__type=REL_SUB_PART_2_ACTIVITY, relations__object_entity=entity.id)
        fields['participants'].q_filter = {'~pk__in': [c.id for c in existing], 'is_user__isnull': True}

        existing_users = [c.is_user.pk for c in existing if c.is_user]
        user_qs = User.objects.exclude(pk__in=existing_users).exclude(pk=user_pk)

        fields['participating_users'].queryset = user_qs
        if not user_qs:
            fields['participating_users'].widget.attrs = {'reduced': 'true'}

        #TODO: refactor this with a smart widget that manages dependencies
        #TODO: hide my participation and my calendar field if logged user already linked ??
        my_participation_field = fields['my_participation']
        my_participation_field.widget.attrs['onclick'] = "if($(this).is(':checked')){$('#id_my_calendar').removeAttr('disabled');}else{$('#id_my_calendar').attr('disabled', 'disabled');}"

        if user_pk in existing_users:
            my_participation_field.initial = True
            my_participation_field.widget.attrs['disabled'] = True

        my_calendar_field = fields['my_calendar']
        my_calendar_field.queryset = Calendar.objects.filter(user=user)
        my_calendar_field.widget.attrs['disabled'] = True

    def clean_participants(self):
        return validate_linkable_entities(self.cleaned_data['participants'], self.user)

    def clean_participating_users(self):
        return validate_linkable_entities(Contact.objects.filter(is_user__in=self.cleaned_data['participating_users']), self.user)

    def clean_my_participation(self):
        my_participation = self.cleaned_data.get('my_participation', False)
        user = self.user

        if my_participation:
            try:
                user_contact = Contact.objects.get(is_user=user)
            except Contact.DoesNotExist:
                warn('No Contact linked to this user: %s', user)
            else:
                self.participants.append(validate_linkable_entity(user_contact, user))

        return my_participation

    def clean(self):
        cleaned_data = self.cleaned_data

        if not self._errors:
            activity = self.activity
            extend_participants = self.participants.extend
            extend_participants(cleaned_data['participating_users'])
            extend_participants(cleaned_data['participants'])

            if cleaned_data['my_participation'] and not cleaned_data.get('my_calendar'):
                self.errors['my_calendar'] = ErrorList([_(u"If you participe, you have to choose one of your calendars.")])

            _check_activity_collisions(activity.start, activity.end, self.participants, busy=activity.busy, exclude_activity_id=activity.id)

        return cleaned_data

    def save(self):
        activity = self.activity

        create_relation = partial(Relation.objects.create, object_entity=activity,
                                  type_id=REL_SUB_PART_2_ACTIVITY, user=activity.user
                                 )

        for participant in self.participants:
            user = participant.is_user
            if user:
                calendar = self.cleaned_data['my_calendar'] if user == self.user else Calendar.get_user_default_calendar(user)
                activity.calendars.add(calendar)

            create_relation(subject_entity=participant)


class SubjectCreateForm(CremeForm):
    subjects = MultiGenericEntityField(label=_(u'Subjects')) #TODO: qfilter to exclude current subjects

    def __init__(self, entity, *args, **kwargs):
        super(SubjectCreateForm, self).__init__(*args, **kwargs)
        self.activity = entity

    def clean_subjects(self):
        return validate_linkable_entities(self.cleaned_data['subjects'], self.user)

    def save (self):
        create_relation = partial(Relation.objects.create, subject_entity=self.activity,
                                  type_id=REL_OBJ_ACTIVITY_SUBJECT, user=self.user
                                 )

        for entity in self.cleaned_data['subjects']:
            create_relation(object_entity=entity)


class ActivityCreateForm(CremeEntityForm):
    class Meta(CremeEntityForm.Meta):
        model = Activity
        exclude = CremeEntityForm.Meta.exclude + ('calendars', )

    start      = CremeDateTimeField(label=_(u'Start'))
    start_time = CremeTimeField(label=_(u'Start time'), required=False)
    end        = CremeDateTimeField(label=_(u'End'), required=False,
                                    help_text=_(u'If you leave end date blank, it will be set up with start date'))
    end_time   = CremeTimeField(label=_(u'End time'), required=False)

    my_participation    = BooleanField(required=False, label=_(u"Do I participate to this meeting ?"),initial=True)
    my_calendar         = ModelChoiceField(queryset=Calendar.objects.none(), required=False, label=_(u"On which of my calendar this activity will appears?"), empty_label=None)
    participating_users = ModelMultipleChoiceField(label=_(u'Other participating users'), queryset=User.objects.all(),
                                                   required=False, widget=UnorderedMultipleChoiceWidget
                                                  )
    other_participants  = MultiCremeEntityField(label=_(u'Other participants'), model=Contact, required=False)
    subjects            = MultiGenericEntityField(label=_(u'Subjects'), required=False)
    linked_entities     = MultiGenericEntityField(label=_(u'Entities linked to this activity'), required=False)

    generate_datetime_alert = BooleanField(label=_(u"Do you want to generate an alert on a specific date ?"), required=False)
    alert_day               = CremeDateTimeField(label=_(u"Alert day"), required=False)
    alert_start_time        = CremeTimeField(label=_(u"Alert time"), required=False)

    generate_period_alert   = BooleanField(label=_(u"Do you want to generate an alert in a while ?"), required=False)
    alert_trigger_number    = IntegerField(label=_(u"Value"), required=False)
    unity                   = ChoiceField(label=_(u"Unity"), choices=UNITY_TAB, required=False)

    blocks = CremeEntityForm.blocks.new(
                ('datetime',       _(u'When'),                   ['start', 'start_time', 'end', 'end_time', 'is_all_day']),
                ('participants',   _(u'Participants'),           ['my_participation', 'my_calendar', 'participating_users', 'other_participants', 'subjects', 'linked_entities']),
                ('alert_datetime', _(u'Generate an alert on a specific date'),  ['generate_datetime_alert', 'alert_day', 'alert_start_time']),
                ('alert_period',   _(u'Generate an alert in a while'),['generate_period_alert', 'alert_trigger_number', 'unity']),
            )

    def __init__(self, *args, **kwargs):
        super(ActivityCreateForm, self).__init__(*args, **kwargs)
        self.participants = [] #all Contacts who participate: me, other users, other contacts

        user =  self.user
        fields = self.fields

        fields['start_time'].initial = time(9, 0)
        fields['end_time'].initial   = time(18, 0)

        my_default_calendar = Calendar.get_user_default_calendar(user) #TODO: variable used once...
        fields['my_calendar'].queryset = Calendar.objects.filter(user=user)
        fields['my_calendar'].initial  = my_default_calendar


#        data = kwargs.get('data') or {}
#        if not data.get('my_participation', False):
#            fields['my_calendar'].widget.attrs['disabled']  = 'disabled'
        #TODO: refactor this with a smart widget that manages dependencies
        fields['my_participation'].widget.attrs['onclick'] = "if($(this).is(':checked')){$('#id_my_calendar').removeAttr('disabled');}else{$('#id_my_calendar').attr('disabled', 'disabled');}"

        fields['participating_users'].queryset = User.objects.exclude(pk=user.id)
        fields['other_participants'].q_filter = {'is_user__isnull': True}

    def clean_my_participation(self):
        my_participation = self.cleaned_data.get('my_participation', False)
        user = self.user

        if my_participation:
            try:
                user_contact = Contact.objects.get(is_user=user)
            except Contact.DoesNotExist:
                warn('No Contact linked to this user: %s', user)
            else:
                self.participants.append(validate_linkable_entity(user_contact, user))

        return my_participation

    def clean_participating_users(self):
        users = self.cleaned_data['participating_users']
        self.participants.extend(validate_linkable_entities(Contact.objects.filter(is_user__in=users), self.user))
        return users

    def clean_other_participants(self):
        participants = self.cleaned_data['other_participants']
        self.participants.extend(validate_linkable_entities(participants, self.user))
        return participants

    def clean_subjects(self):
        return validate_linkable_entities(self.cleaned_data['subjects'], self.user)

    def clean_linked_entities(self):
        return validate_linkable_entities(self.cleaned_data['linked_entities'], self.user)

    def clean(self):
        cleaned_data = self.cleaned_data

        if not self._errors:
            _clean_interval(cleaned_data)

            if cleaned_data['my_participation'] and not cleaned_data.get('my_calendar'):
                self.errors['my_calendar'] = ErrorList([_(u"If you participe, you have to choose one of your calendars.")])

            _check_activity_collisions(cleaned_data['start'], cleaned_data['end'], self.participants, busy=cleaned_data['busy'])

        return cleaned_data

    def save(self):
        instance     = self.instance
        cleaned_data = self.cleaned_data

        super(ActivityCreateForm, self).save()

        self._generate_alert()

        if cleaned_data['my_participation']:
            instance.calendars.add(cleaned_data['my_calendar'])

        for part_user in cleaned_data['participating_users']:
            #TODO: regroup queries ??
            instance.calendars.add(Calendar.get_user_default_calendar(part_user))

        create_relation = partial(Relation.objects.create, object_entity=instance, user=instance.user)

        for participant in self.participants:
            create_relation(subject_entity=participant, type_id=REL_SUB_PART_2_ACTIVITY)

        for subject in cleaned_data['subjects']:
            create_relation(subject_entity=subject, type_id=REL_SUB_ACTIVITY_SUBJECT)

        for linked in cleaned_data['linked_entities']:
            create_relation(subject_entity=linked, type_id=REL_SUB_LINKED_2_ACTIVITY)

        return instance

    _TIME_DELTA = {
            MINUTE: 'minutes',
            HOUR:   'hours',
            DAY:    'days',
            WEEK:   'weeks',
        }

    def _generate_alert(self):
        cleaned_data = self.cleaned_data

        if cleaned_data['generate_datetime_alert']:
            activity = self.instance

            alert_start_time = cleaned_data.get('alert_start_time') or time()
            alert_day        = cleaned_data.get('alert_day') or activity.start

            Alert.objects.create(user=activity.user,
                                 trigger_date=alert_day.replace(hour=alert_start_time.hour, minute=alert_start_time.minute),
                                 creme_entity=activity,
                                 title=ugettext(u"Alert of activity"),
                                 description=ugettext(u'Alert related to %s') % activity,
                                )
            
        if cleaned_data['generate_period_alert']:
            activity = self.instance
            unity = cleaned_data['unity']
            value = cleaned_data['alert_trigger_number']

            if value and unity:
                Alert.objects.create(user=activity.user,
                                     trigger_date=datetime.today() + timedelta(**{self._TIME_DELTA[unity]: value}),
                                     creme_entity=activity,
                                     title=ugettext(u"Alert of activity"),
                                     description=ugettext(u'Alert related to %s') % activity,
                                    )


class RelatedActivityCreateForm(ActivityCreateForm):
    def __init__(self, entity_for_relation, relation_type, *args, **kwargs):
        super(RelatedActivityCreateForm, self).__init__(*args, **kwargs)
        self.entity_for_relation = entity_for_relation
        fields = self.fields
        rtype_id = relation_type.id

        if rtype_id == REL_SUB_PART_2_ACTIVITY:
            assert isinstance(entity_for_relation, Contact)

            if entity_for_relation.is_user:
                fields['participating_users'].initial = [entity_for_relation.is_user]
            else:
                fields['other_participants'].initial = [entity_for_relation.id]
        elif rtype_id == REL_SUB_ACTIVITY_SUBJECT:
            fields['subjects'].initial = [entity_for_relation]
        else:
            assert rtype_id == REL_SUB_LINKED_2_ACTIVITY
            fields['linked_entities'].initial = [entity_for_relation]


#TODO: factorise ?? (ex: CreateForm inherits from EditForm....)
class ActivityEditForm(CremeEntityForm):
    start      = CremeDateTimeField(label=_(u'Start'))
    start_time = CremeTimeField(label=_(u'Start time'), required=False)
    end        = CremeDateTimeField(label=_(u'End'), required=False,
                                    help_text=_(u'If you leave end date blank, it will be set up with start date'))
    end_time   = CremeTimeField(label=_(u'End time'), required=False)

    class Meta(CremeEntityForm.Meta):
        model = Activity
        exclude = CremeEntityForm.Meta.exclude + ('type', 'calendars')

    def __init__(self, *args, **kwargs):
        super(ActivityEditForm, self).__init__(*args, **kwargs)

        fields = self.fields
        instance = self.instance

        fields['start_time'].initial = instance.start.time()
        fields['end_time'].initial   = instance.end.time()

        if instance.type.is_custom:
            fields['type'] = instance._meta.get_field('type').formfield(queryset=ActivityType.objects.filter(is_custom=True), initial=instance.type.id)

    def clean(self):
        cleaned_data = self.cleaned_data

        if self._errors:
            return cleaned_data

        instance = self.instance

        _clean_interval(cleaned_data)

        # check if activity period change cause collisions
        _check_activity_collisions(cleaned_data['start'], cleaned_data['end'],
                                   instance.get_related_entities(REL_OBJ_PART_2_ACTIVITY),
                                   busy=cleaned_data['busy'], exclude_activity_id=instance.id
                                  )

        return cleaned_data

    def save(self):
        self.instance.end = self.cleaned_data['end']

        activity_type = self.cleaned_data.get('type')
        if activity_type is not None and self.instance.type.is_custom:
            self.instance.type = activity_type

        return super(ActivityEditForm, self).save()

class CustomActivityCreateForm(ActivityCreateForm):
    type = CreatorModelChoiceField(label=_('Activity type'), 
                                   queryset=ActivityType.objects.filter(is_custom=True),
                                   required=True, initial=None)

    def __init__(self, *args, **kwargs):
        super(CustomActivityCreateForm, self).__init__(*args, **kwargs)
        self.fields['type'].user = self.user
        #self.fields['type'].queryset = self.fields['type'].queryset.filter(is_custom=True)

        if self.fields['type'].queryset.count() == 0:
            self.fields['type'].help_text = _(u"No custom activity type, you should create one in configuration in order to create an activity.")


class RelatedCustomActivityCreateForm(RelatedActivityCreateForm):
    def __init__(self, *args, **kwargs):
        super(RelatedCustomActivityCreateForm, self).__init__(*args, **kwargs)
        self.fields['type'].queryset = self.fields['type'].queryset.filter(is_custom=True)

        if self.fields['type'].queryset.count() == 0:
            self.fields['type'].help_text = _(u"No custom activity type, you should create one in configuration in order to create an activity.")


_ACTIVITY_TYPE_EXCLUDED_FROM_POPUP = [ACTIVITYTYPE_SHOW, ACTIVITYTYPE_TASK, ACTIVITYTYPE_GATHERING,
                                      ACTIVITYTYPE_DEMO, ACTIVITYTYPE_INDISPO]

_ACTIVITY_TYPE_MAP = {ACTIVITYTYPE_PHONECALL: PhoneCall,
                      ACTIVITYTYPE_MEETING:   Meeting
                     }

class CalendarActivityCreateForm(ActivityCreateForm):
    start = DateTimeField(label=_(u'Start'))

    blocks = FieldBlockManager(
        ('general',        _(u'General information'),           ['user', 'title', 'description', 'type']),
        ('datetime',       _(u'When'),                          ['start', 'start_time', 'end', 'end_time', 'is_all_day']),
        ('participants',   _(u'Participants'),                  ['my_participation', 'my_calendar', 'participating_users',
                                                                 'other_participants', 'subjects', 'linked_entities']),
        ('alert_period',   _(u'Generate an alert in a while'),  ['alert_trigger_number', 'unity']),
    )

    class Meta:
        model = Activity
        exclude = ActivityCreateForm.Meta.exclude + ('calendars', 'minutes', 'is_comapp', 'place', 'call_type'
                                                     'generate_datetime_alert', 'alert_day', 'alert_start_time')

    def __init__(self, start=None, *args, **kwargs):
        super(CalendarActivityCreateForm, self).__init__(*args, **kwargs)

        fields = self.fields
        field_start = fields['start']

        fields['end'].help_text = ""
        fields['busy'].initial = False
        fields['type'].queryset = ActivityType.objects.exclude(pk__in=_ACTIVITY_TYPE_EXCLUDED_FROM_POPUP)

        fields['participating_users'].widget.attrs = {'reduced':'true'}

        if start:
            field_start.initial = start
            fields['end'].initial = start

            hour = start.hour
            minute = start.minute
            if hour or minute:
                start_time = time(hour=hour, minute=minute)
                fields['start_time'].initial = start_time
                # TODO arbitrary duration (1h), we don't know, at this point, the activity type, to retrieve its default duration
                fields['end_time'].initial = time(start_time.hour + 1, start_time.minute)

    def clean_type(self):
        type = self.cleaned_data['type']
        self.instance = _ACTIVITY_TYPE_MAP.get(type.id, Activity)()
        return type
