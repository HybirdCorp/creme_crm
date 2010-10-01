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

from django.forms.util import ValidationError
from django.forms import IntegerField, CharField, BooleanField, ModelMultipleChoiceField
from django.forms.widgets import CheckboxSelectMultiple
from django.utils.translation import ugettext as _, ugettext
from django.db.models import Q
from django.contrib.auth.models import User

from creme_core.models import CremeEntity, Relation, RelationType
from creme_core.forms import CremeForm, CremeEntityForm, RelatedEntitiesField, CremeDateTimeField, CremeTimeField
from creme_core.forms.widgets import Label

from persons.models import Contact

from activities.models import Activity
from activities.constants import *


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
        _check_activity_collisions(activity.start, activity.end,
                                   [entity for rtype, entity in cleaned_data['participants']])

        return cleaned_data

    def save (self):
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

    is_comapp        = BooleanField(required=False, label=_(u"Is a commercial approach ?"))
    my_participation = BooleanField(required=False, label=_(u"Do I participate to this meeting ?"))
    participants     = RelatedEntitiesField(relation_types=[REL_SUB_ACTIVITY_SUBJECT, REL_SUB_PART_2_ACTIVITY, REL_SUB_LINKED_2_ACTIVITY],
                                            label=_(u'Other participants'), required=False)

    informed_users = ModelMultipleChoiceField(queryset=User.objects.all(),
                                              widget=CheckboxSelectMultiple(),
                                              required=False, label=_(u"Users"))

    blocks = CremeEntityForm.blocks.new(
                ('datetime',       _(u'When'),                   ['start', 'start_time', 'end_time', 'is_all_day']),
                ('participants',   _(u'Participants'),           ['my_participation', 'participants']),
                ('informed_users', _(u'Users to keep informed'), ['informed_users']),
            )

    def __init__(self, *args, **kwargs):
        super(_ActivityCreateBaseForm, self).__init__(*args, **kwargs)
        fields = self.fields

        fields['start_time'].initial = time(9, 0)
        fields['end_time'].initial   = time(18, 0)

    def clean(self):
        if self._errors:
            return self.cleaned_data

        _clean_interval(self.cleaned_data)
        self.check_activities()

        return self.cleaned_data

    # TODO : check for activities in same range for participants
    def check_activities(self):
        cleaned_data = self.cleaned_data
        participants = [entity for rtype, entity in cleaned_data['participants']]

        if cleaned_data.get('my_participation'):
            try:
                participants.append(Contact.objects.filter(is_user=cleaned_data['user'])[0]) #TODO: get() instead of filter() ??
            except IndexError:
                pass

        _check_activity_collisions(cleaned_data['start'], cleaned_data['end'], participants)

    def save(self):
        instance     = self.instance
        cleaned_data = self.cleaned_data

        instance.end = cleaned_data['end']
        super(_ActivityCreateBaseForm, self).save()

        # Participation of event's creator
        if cleaned_data['my_participation']:
            try:
                me = Contact.objects.filter(is_user=cleaned_data['user'])[0] #get() instead ???
            except IndexError:
                pass
            else:
                Relation.create(me, REL_SUB_PART_2_ACTIVITY, instance)

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
        super(ActivityCreateForm, self).save()

        Relation.create(self._entity_for_relation, self._relation_type.id, self.instance)

        if self.cleaned_data.get('is_comapp', False):
            self._create_commercial_approach(self._entity_for_relation)


class ActivityCreateWithoutRelationForm(_ActivityCreateBaseForm):
    def __init__(self, *args, **kwargs):
        super(ActivityCreateWithoutRelationForm, self).__init__(*args, **kwargs)
        self.fields['is_comapp'].help_text = ugettext(u"Add participants to them be linked to a commercial approach.")

    def save(self):
        super(ActivityCreateWithoutRelationForm, self).save()

        if self.cleaned_data.get('is_comapp', False):
            self._create_commercial_approach()


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
        _check_activity_collisions(cleaned_data['start'], cleaned_data['end'],
                                   instance.get_related_entities(REL_OBJ_PART_2_ACTIVITY),
                                   instance.id)

        return cleaned_data

    def save(self):
        self.instance.end = self.cleaned_data['end']
        super(ActivityEditForm, self).save()
