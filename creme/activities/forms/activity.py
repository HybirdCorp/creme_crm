# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from logging import debug
from datetime import datetime, time

from django.forms.models import ModelChoiceField
from django.forms.util import ValidationError, ErrorList
from django.forms import IntegerField, CharField, BooleanField, ModelMultipleChoiceField
from django.forms.widgets import CheckboxSelectMultiple
from django.utils.translation import ugettext as _, ugettext
from django.db.models import Q
from django.contrib.auth.models import User

from creme_core.models import CremeEntity, Relation, RelationType
from creme_core.forms import CremeForm, CremeEntityForm, RelatedEntitiesField, CremeDateTimeField, CremeTimeField
from creme_core.forms.widgets import Label

from persons.models import Contact

from activities.models import Activity, Calendar, CalendarActivityLink
from activities.constants import *

from assistants.models.alert import Alert

def _generate_alert(phone_call, cleaned_data):
    if cleaned_data['generate_alert']:
        alert_start_time = cleaned_data.get('alert_start_time') or time()
        alert_day        = cleaned_data.get('alert_day') or phone_call.start

        alert = Alert()
        alert.for_user     = phone_call.user
        alert.trigger_date = alert_day.replace(hour=alert_start_time.hour, minute=alert_start_time.minute)
        alert.creme_entity = phone_call
        alert.title        = ugettext(u"Alert of phone call")
        alert.description  = ugettext(u'Alert related to a phone call')
        alert.save()


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
    collision_test = ~(Q(end__lte=activity_start) | Q(start__gte=activity_end))
    collisions     = []

    for participant in participants:
        # find activities of participant
        activity_req = Relation.objects.filter(subject_entity=participant.id, type=REL_SUB_PART_2_ACTIVITY)

        # exclude current activity if asked
        if exclude_activity_id is not None:
            activity_req = activity_req.exclude(object_entity=exclude_activity_id)

        # get id of activities of participant
        activity_ids = activity_req.values_list("object_entity__id", flat=True)

        # do collision request
        #TODO: can be done with less queries ?
        #  eg:  Activity.objects.filter(relations__object_entity=participant.id, relations__object_entity__type=REL_OBJ_PART_2_ACTIVITY).filter(collision_test)
        #activity_collisions = Activity.objects.exclude(occuped=False).filter(pk__in=activity_ids).filter(collision_test)[:1]
        activity_collisions = Activity.objects.filter(pk__in=activity_ids).filter(collision_test)[:1]

        if activity_collisions:
            collision = activity_collisions[0]
            collision_start = max(activity_start.time(), collision.start.time())
            collision_end   = min(activity_end.time(),   collision.end.time())

            collisions.append(ugettext(u"%(participant)s already participates to the activity «%(activity)s» between %(start)s and %(end)s.") % {
                        'participant': participant,
                        'activity':    collision,
                        'start':       collision_start,
                        'end':         collision_end,
                    })

    if collisions:
        raise ValidationError(collisions)

def _save_participants(participants, instance):
    """
    @param participants sequence of tuple relationtype_id, entity (see RelatedEntitiesField)
    """
    create_relation = Relation.create

    for relationtype_id, entity in participants:
        create_relation(entity, relationtype_id, instance)

class ParticipantCreateForm(CremeForm):
    participants = RelatedEntitiesField(relation_types=[REL_SUB_PART_2_ACTIVITY], label=_(u'Participants'), required=False)

    def __init__(self, activity, *args, **kwargs):
        super(ParticipantCreateForm, self).__init__(*args, **kwargs)
        self.activity = activity

    def clean(self):
        cleaned_data = self.cleaned_data

        if self._errors:
            return cleaned_data

        activity = self.activity
        if activity.occuped :
            _check_activity_collisions(activity.start, activity.end,
                                   [entity for rtype, entity in cleaned_data['participants']])

        return cleaned_data

    def save(self):
        _save_participants(self.cleaned_data['participants'], self.activity)


class SubjectCreateForm(CremeForm):
    subjects = RelatedEntitiesField(relation_types=[REL_SUB_ACTIVITY_SUBJECT], label=_(u'Subjects'), required=False)

    def __init__(self, activity, *args, **kwargs):
        super(SubjectCreateForm, self).__init__(*args, **kwargs)
        self.activity = activity

    def save (self):
        _save_participants(self.cleaned_data['subjects'], self.activity)


class _ActivityCreateBaseForm(CremeEntityForm):
    class Meta(CremeEntityForm.Meta):
        model = Activity
        exclude = CremeEntityForm.Meta.exclude + ('end',)

    start      = CremeDateTimeField(label=_(u'Start'))
    start_time = CremeTimeField(label=_(u'Start time'), required=False)
    end_time   = CremeTimeField(label=_(u'End time'), required=False)

    is_comapp          = BooleanField(required=False, label=_(u"Is a commercial approach ?"))
    my_participation   = BooleanField(required=False, label=_(u"Do I participate to this meeting ?"))
    my_calendar        = ModelChoiceField(queryset=Calendar.objects.none(), required=False, label=_(u"On which of my calendar this activity will appears?"), empty_label=None)
    user_participation = BooleanField(required=False, label=_(u"Do the responsable of this file participate to this meeting ? (Currently %s)"))
    participants       = RelatedEntitiesField(relation_types=[REL_SUB_ACTIVITY_SUBJECT, REL_SUB_PART_2_ACTIVITY, REL_SUB_LINKED_2_ACTIVITY],
                                            label=_(u'Other participants'), required=False)

    generate_alert   = BooleanField(label=_(u"Do you want to generate an alert or a reminder ?"), required=False)
    alert_day        = CremeDateTimeField(label=_(u"Alert day"), required=False)
    alert_start_time = CremeTimeField(label=_(u"Alert time"), required=False)
    

    #informed_users = ModelMultipleChoiceField(queryset=User.objects.all(),
                                              #widget=CheckboxSelectMultiple(),
                                              #required=False, label=_(u"Users"))

    blocks = CremeEntityForm.blocks.new(
                ('datetime',       _(u'When'),                   ['start', 'start_time', 'end_time', 'is_all_day']),
                ('participants',   _(u'Participants'),           ['my_participation', 'my_calendar', 'user_participation', 'participants']),
                ('alert_datetime', _(u'Generate an alert or a reminder'), ['generate_alert', 'alert_day', 'alert_start_time']),
                #('informed_users', _(u'Users to keep informed'), ['informed_users']),
            )

    

    def __init__(self, current_user, *args, **kwargs):
        super(_ActivityCreateBaseForm, self).__init__(*args, **kwargs)
        self.current_user = current_user
        data = kwargs.get('data')

        fields = self.fields

        fields['start_time'].initial = time(9, 0)
        fields['end_time'].initial   = time(18, 0)

        user_field = fields['user']
        fields['user_participation'].label %= user_field.queryset[0] if user_field.queryset else _(u"Nobody")
        user_field.widget.attrs['onchange'] = "$('label[for=id_user_participation]').html('%s (%s '+this.options[this.selectedIndex].innerHTML+')');" % (_(u"Do the responsable of this file participate to this meeting ?"), _(u"Currently"))

        my_default_calendar = Calendar.get_user_default_calendar(current_user)
        fields['my_calendar'].queryset = Calendar.objects.filter(user=current_user)
        fields['my_calendar'].initial  = my_default_calendar

        if data is None or not data.get('my_participation', False):
            fields['my_calendar'].widget.attrs['disabled']  = 'disabled'
        fields['my_participation'].widget.attrs['onclick'] = "if($(this).is(':checked')){$('#id_my_calendar').removeAttr('disabled');}else{$('#id_my_calendar').attr('disabled', 'disabled');}"

    def clean(self):
        if self._errors:
            return self.cleaned_data

        cleaned_data = self.cleaned_data
        errors       = self.errors

        _clean_interval(self.cleaned_data)
        self.check_activities()

        my_participation = cleaned_data.get('my_participation')
        if my_participation and not cleaned_data.get('my_calendar'):
            errors['my_calendar'] = ErrorList([_(u"If you participe, you have to choose one of your calendars.")])

        if not my_participation and not cleaned_data.get('user_participation'):
            errors['my_participation']   = ErrorList([_(u"You or the assigned user has to participate")])
            errors['user_participation'] = ErrorList([_(u"You or the assigned user has to participate")])

        return self.cleaned_data

    # TODO : check for activities in same range for participants
    def check_activities(self):
        cleaned_data = self.cleaned_data
        participants = [entity for rtype, entity in cleaned_data['participants']]

        if cleaned_data.get('user_participation'):
            try:
                participants.append(Contact.objects.get(is_user=cleaned_data['user']))
            except Contact.DoesNotExist:
                pass

        if cleaned_data.get('my_participation'):
            try:
                participants.append(Contact.objects.get(is_user=self.current_user))
            except Contact.DoesNotExist:
                pass
        if cleaned_data['occuped']:
            _check_activity_collisions(cleaned_data['start'], cleaned_data['end'], participants)

    def save(self):
        instance     = self.instance
        cleaned_data = self.cleaned_data

        instance.end = cleaned_data['end']

        super(_ActivityCreateBaseForm, self).save()

        _generate_alert(instance, self.cleaned_data)

        # Participation of event's creator
        if cleaned_data['my_participation']:
            try:
                me = Contact.objects.get(is_user=self.current_user)
            except Contact.DoesNotExist:
                pass
            else:
                Relation.create(me, REL_SUB_PART_2_ACTIVITY, instance)
                CalendarActivityLink.objects.get_or_create(calendar=cleaned_data.get('my_calendar'), activity=instance)

        # Participation of event's owner
        if cleaned_data['user_participation']:
            user = cleaned_data['user']
            try:
                me = Contact.objects.get(is_user=user)
            except Contact.DoesNotExist:
                pass
            else:
                Relation.create(me, REL_SUB_PART_2_ACTIVITY, instance)
                CalendarActivityLink.objects.get_or_create(calendar=Calendar.get_user_default_calendar(user), activity=instance)

        _save_participants(cleaned_data['participants'], instance)

        return instance

    #TODO: inject from 'commercial' app instead ??
    def _create_commercial_approach(self, extra_entity=None):
        from commercial.models import CommercialApproach

        participants = [entity for rtype, entity in self.cleaned_data['participants']]

        if extra_entity:
            participants.append(extra_entity)

        if not participants:
            return

        now = datetime.now()
        instance = self.instance
        create_comapp = CommercialApproach.objects.create

        for participant in participants:
            create_comapp(title=instance.title,
                          description=instance.description,
                          creation_date=now,
                          creme_entity=participant,
                          related_activity_id=instance.id,
                         )


class ActivityCreateForm(_ActivityCreateBaseForm):
    entity_preview        = CharField(label=_(u'Who / What'), required=False, widget=Label)
    relation_type_preview = CharField(label=_(u'Relation with the activity'), required=False, widget=Label)

    def __init__(self, entity_for_relation, relation_type, *args, **kwargs):
        super(ActivityCreateForm, self).__init__(*args, **kwargs)

        self._entity_for_relation = entity_for_relation
        self._relation_type = relation_type

        fields = self.fields
        fields['entity_preview'].initial =  entity_for_relation
        fields['relation_type_preview'].initial = relation_type.predicate

    def save(self):
        instance = super(ActivityCreateForm, self).save()

        Relation.create(self._entity_for_relation, self._relation_type.id, self.instance)

        if self.cleaned_data.get('is_comapp', False):
            self._create_commercial_approach(self._entity_for_relation)

        return instance


class ActivityCreateWithoutRelationForm(_ActivityCreateBaseForm):
    def __init__(self, *args, **kwargs):
        super(ActivityCreateWithoutRelationForm, self).__init__(*args, **kwargs)
        self.fields['is_comapp'].help_text = ugettext(u"Add participants to them be linked to a commercial approach.")

    def save(self):
        instance = super(ActivityCreateWithoutRelationForm, self).save()

        if self.cleaned_data.get('is_comapp', False):
            self._create_commercial_approach()
        return instance


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
        if cleaned_data['occuped']:
            _check_activity_collisions(cleaned_data['start'], cleaned_data['end'],
                                   instance.get_related_entities(REL_OBJ_PART_2_ACTIVITY),
                                   instance.id)

        return cleaned_data

    def save(self):
        self.instance.end = self.cleaned_data['end']
        return super(ActivityEditForm, self).save()
