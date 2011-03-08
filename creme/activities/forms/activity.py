# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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
from datetime import datetime, time
from logging import debug

from django.forms import IntegerField, BooleanField, ModelChoiceField, ModelMultipleChoiceField
from django.forms.util import ValidationError, ErrorList
from django.utils.translation import ugettext_lazy as _, ugettext
from django.db.models import Q
from django.contrib.auth.models import User

from creme_core.models import Relation, RelationType
from creme_core.forms import CremeForm, CremeEntityForm
from creme_core.forms.fields import CremeDateTimeField, CremeTimeField, MultiCremeEntityField, MultiGenericEntityField
from creme_core.forms.widgets import UnorderedMultipleChoiceWidget
from creme_core.forms.validators import validate_linkable_entities, validate_linkable_entity

from persons.models import Contact

from assistants.models.alert import Alert

from activities.models import Activity, Calendar, CalendarActivityLink
from activities.constants import *
from activities.utils import check_activity_collisions


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

def _check_activity_collisions(activity_start, activity_end, participants, exclude_activity_id=None):
    collisions = check_activity_collisions(activity_start, activity_end, participants, exclude_activity_id=exclude_activity_id)
    if collisions:
        raise ValidationError(collisions)

#TODO: factorise with ActivityCreateForm ??
class ParticipantCreateForm(CremeForm):
    participants = MultiCremeEntityField(label=_(u'Participants'), model=Contact)

    def __init__(self, entity, *args, **kwargs):
        super(ParticipantCreateForm, self).__init__(*args, **kwargs)
        self.activity = entity
        self.participants = []

        existing = Contact.objects.filter(relations__type=REL_SUB_PART_2_ACTIVITY, relations__object_entity=entity.id)
        self.fields['participants'].q_filter = {'~pk__in': [c.id for c in existing]}

    def clean_participants(self):
        return validate_linkable_entities(self.cleaned_data['participants'], self.user)

    def clean(self):
        cleaned_data = self.cleaned_data

        if not self._errors:
            activity = self.activity
            self.participants += cleaned_data['participants']

            if activity.busy:
                _check_activity_collisions(activity.start, activity.end, self.participants)

        return cleaned_data

    def save(self):
        activity = self.activity
        create_link = CalendarActivityLink.objects.get_or_create
        create_relation = partial(Relation.objects.create, object_entity=activity,
                                  type_id=REL_SUB_PART_2_ACTIVITY, user=activity.user
                                 )

        for participant in self.participants:
            if participant.is_user:
                create_link(calendar=Calendar.get_user_default_calendar(participant.is_user), activity=activity)

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
        exclude = CremeEntityForm.Meta.exclude + ('end',)

    start      = CremeDateTimeField(label=_(u'Start'))
    start_time = CremeTimeField(label=_(u'Start time'), required=False)
    end_time   = CremeTimeField(label=_(u'End time'), required=False)


    my_participation    = BooleanField(required=False, label=_(u"Do I participate to this meeting ?"),initial=True)
    my_calendar         = ModelChoiceField(queryset=Calendar.objects.none(), required=False, label=_(u"On which of my calendar this activity will appears?"), empty_label=None)
    participating_users = ModelMultipleChoiceField(label=_(u'Other participating users'), queryset=User.objects.all(),
                                                   required=False, widget=UnorderedMultipleChoiceWidget
                                                  )
    other_participants  = MultiCremeEntityField(label=_(u'Other participants'), model=Contact, required=False)
    subjects            = MultiGenericEntityField(label=_(u'Subjects'), required=False)
    linked_entities     = MultiGenericEntityField(label=_(u'Entities linked to this activity'), required=False)


    generate_alert   = BooleanField(label=_(u"Do you want to generate an alert or a reminder ?"), required=False)
    alert_day        = CremeDateTimeField(label=_(u"Alert day"), required=False)
    alert_start_time = CremeTimeField(label=_(u"Alert time"), required=False)

    blocks = CremeEntityForm.blocks.new(
                ('datetime',       _(u'When'),                   ['start', 'start_time', 'end_time', 'is_all_day']),
                ('participants',   _(u'Participants'),           ['my_participation', 'my_calendar', 'participating_users', 'other_participants', 'subjects', 'linked_entities']),
                ('alert_datetime', _(u'Generate an alert or a reminder'), ['generate_alert', 'alert_day', 'alert_start_time']),
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

        try:
            user_contact = Contact.objects.get(is_user=user)
        except Contact.DoesNotExist:
            debug('No Contact linked to this user: %s', user)
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

            if cleaned_data['busy']:
                _check_activity_collisions(cleaned_data['start'], cleaned_data['end'], self.participants)

        return cleaned_data

    def save(self):
        instance     = self.instance
        cleaned_data = self.cleaned_data

        instance.end = cleaned_data['end']
        super(ActivityCreateForm, self).save()

        self._generate_alert()

        create_link = CalendarActivityLink.objects.get_or_create

        if cleaned_data['my_participation']:
            create_link(calendar=cleaned_data['my_calendar'], activity=instance)

        for part_user in cleaned_data['participating_users']:
            #TODO: regroup queries ??
            create_link(calendar=Calendar.get_user_default_calendar(part_user), activity=instance)

        create_relation = partial(Relation.objects.create, object_entity=instance, user=instance.user)

        for participant in self.participants:
            create_relation(subject_entity=participant, type_id=REL_SUB_PART_2_ACTIVITY)

        for subject in cleaned_data['subjects']:
            create_relation(subject_entity=subject, type_id=REL_SUB_ACTIVITY_SUBJECT)

        for linked in cleaned_data['linked_entities']:
            create_relation(subject_entity=linked, type_id=REL_SUB_LINKED_2_ACTIVITY)

        return instance

    def _generate_alert(self):
        cleaned_data = self.cleaned_data

        if cleaned_data['generate_alert']:
            activity = self.instance

            alert_start_time = cleaned_data.get('alert_start_time') or time()
            alert_day        = cleaned_data.get('alert_day') or activity.start

            Alert.objects.create(for_user=activity.user,
                                 trigger_date=alert_day.replace(hour=alert_start_time.hour, minute=alert_start_time.minute),
                                 creme_entity=activity,
                                 title=ugettext(u"Alert of activity"),
                                 description=ugettext(u'Alert related to %s') % activity,
                                )


class RelatedActivityCreateForm(ActivityCreateForm):
    def __init__(self, entity_for_relation, relation_type, *args, **kwargs):
        super(RelatedActivityCreateForm, self).__init__(*args, **kwargs)
        fields = self.fields
        rtype_id = relation_type.id

        if rtype_id == REL_SUB_PART_2_ACTIVITY:
            assert isinstance(entity_for_relation, Contact)

            if entity_for_relation.is_user:
                self.fields['participating_users'].initial = [entity_for_relation.is_user]
            else:
                self.fields['other_participants'].initial = entity_for_relation.id
        elif rtype_id == REL_SUB_ACTIVITY_SUBJECT:
            self.fields['subjects'].initial = [entity_for_relation]
        else:
            assert rtype_id == REL_SUB_LINKED_2_ACTIVITY
            self.fields['linked_entities'].initial = [entity_for_relation]


#TODO: factorise ?? (ex: CreateForm inherits from EditForm....)
class ActivityEditForm(CremeEntityForm):
    start      = CremeDateTimeField(label=_(u'Start'))
    start_time = CremeTimeField(label=_(u'Start time'), required=False)
    end_time   = CremeTimeField(label=_(u'End time'), required=False)

    class Meta(CremeEntityForm.Meta):
        model = Activity
        exclude = CremeEntityForm.Meta.exclude + ('end', 'type')

    def __init__(self, *args, **kwargs):
        super(ActivityEditForm, self).__init__(*args, **kwargs)

        fields = self.fields
        instance = self.instance

        fields['start_time'].initial = instance.start.time()
        fields['end_time'].initial   = instance.end.time()

    def clean(self):
        cleaned_data = self.cleaned_data

        if self._errors:
            return cleaned_data

        instance = self.instance

        _clean_interval(cleaned_data)

        # check if activity period change cause collisions
        if cleaned_data['busy']:
            _check_activity_collisions(cleaned_data['start'], cleaned_data['end'],
                                       instance.get_related_entities(REL_OBJ_PART_2_ACTIVITY),
                                       instance.id
                                      )

        return cleaned_data

    def save(self):
        self.instance.end = self.cleaned_data['end']
        return super(ActivityEditForm, self).save()
