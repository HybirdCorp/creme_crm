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

from logging import debug #raiseExceptions
import re, datetime

from django.forms.util import ValidationError
from django.forms import Form, IntegerField, CharField, DateTimeField, BooleanField, ModelChoiceField, DateField, TimeField, ModelMultipleChoiceField
from django.forms.widgets import HiddenInput, CheckboxSelectMultiple, TextInput
from django.utils.translation import ugettext as _
from django.db.models import Q
from django.contrib.auth.models import User

from creme_core.models import CremeEntity, Relation, RelationType
from creme_core.forms import CremeModelForm, CremeForm
from creme_core.forms.fields import RelatedEntitiesField
from creme_core.forms.widgets import CalendarWidget, TimeWidget, RelationListWidget

from persons.models.contact import Contact

from activities.models import Activity
from activities.constants import REL_SUB_PART_2_ACTIVITY, REL_SUB_ACTIVITY_SUBJECT, REL_SUB_LINKED_2_ACTIVITY


class ParticipantCreateForm(CremeForm):
    participants = RelatedEntitiesField(relations=[REL_SUB_PART_2_ACTIVITY],
                                        label=_(u'Participants'),
                                        widget=RelationListWidget(),
                                        required=False)

    def __init__(self, activity, *args, **kwargs):
        super(ParticipantCreateForm, self).__init__(*args, **kwargs)
        self.activity = activity

        #ActivityCreateForm.init_participants_widget(self.fields.get('participants'), [REL_SUB_PART_2_ACTIVITY])

    def clean(self):
        cleaned_data = self.cleaned_data

        if self._errors:
            return cleaned_data

        participants = [pk for rtype, pk in cleaned_data.get('participants')]
        activity = self.activity
        ActivityCreateForm.check_activity_collisions(activity.start, activity.end, participants)

        return cleaned_data

    def save (self):
        participants = self.cleaned_data.get('participants', [])
        ActivityCreateForm.save_other_participants(participants, self.activity)


class SubjectCreateForm(CremeForm):
    subjects = RelatedEntitiesField(relations=[REL_SUB_ACTIVITY_SUBJECT],
                                        label=_(u'Sujets'),
                                        widget=RelationListWidget(),
                                        required=False)

    def __init__(self, activity, *args, **kwargs):
        super(SubjectCreateForm, self).__init__(*args, **kwargs)
        self.activity = activity

        #ActivityCreateForm.init_participants_widget(self.fields.get('subjects'), [REL_SUB_ACTIVITY_SUBJECT])

    def save (self):
        subjects = self.cleaned_data.get('subjects', [])
        ActivityCreateForm.save_other_participants(subjects, self.activity)

class _ActivityCreateBaseForm(CremeModelForm):
    class Meta:
        model = Activity
        exclude = ['is_actived', 'is_deleted', 'end']

    start      = DateTimeField(label=_(u'Début'), widget=CalendarWidget())
    start_time = TimeField(label=_(u'Heure de début'), widget=TimeWidget(), required=False)
    end_time   = TimeField(label=_(u'Heure de fin'), widget=TimeWidget(), required=False)
    
    is_comapp        = BooleanField(required=False, label=_(u"Est une démarche commerciale ?"))
    my_participation = BooleanField(required=False, label=_(u"Est-ce que je participe à ce rendez-vous ?"))
    participants     = RelatedEntitiesField(relations=[REL_SUB_ACTIVITY_SUBJECT, REL_SUB_PART_2_ACTIVITY, REL_SUB_LINKED_2_ACTIVITY],
                                            label=_(u'Autres participants'),
                                            widget=RelationListWidget(),
                                            required=False)
                                            
    informed_users   = ModelMultipleChoiceField(queryset=User.objects.all(),
                                                widget=CheckboxSelectMultiple(),
                                                required=False,
                                                label=_(u"Utilisateurs") )

    blocks = CremeModelForm.blocks.new(
                ('datetime',       _(u'Quand'),  ['start', 'start_time', 'end_time', 'is_all_day']),
                ('participants',   _(u'Participants'), ['my_participation', 'participants']),
                ('informed_users', _(u'Les utilisateurs à tenir informés'), ['informed_users',]),
            )

    def __init__(self, *args, **kwargs):
        super(_ActivityCreateBaseForm, self).__init__(*args, **kwargs)
        fields = self.fields

        fields['start_time'].initial = datetime.time(9, 0)
        fields['end_time'].initial = datetime.time(18, 0)

    @staticmethod
    def clean_interval(cleaned_data):
        if cleaned_data.get('is_all_day'):
            cleaned_data['start_time'] = datetime.time(hour=0,  minute=0)
            cleaned_data['end_time']   = datetime.time(hour=23, minute=59)

        start_time = cleaned_data.get('start_time', datetime.time())
        end_time   = cleaned_data.get('end_time',   datetime.time())

        cleaned_data['start'] = cleaned_data['start'].replace(hour=start_time.hour, minute=start_time.minute)

        if not cleaned_data.get('end'):
            cleaned_data['end'] = cleaned_data['start']

        cleaned_data['end'] = cleaned_data['end'].replace(hour=end_time.hour, minute=end_time.minute)

        if cleaned_data['start'] > cleaned_data['end']:
            raise ValidationError(u"L'heure de fin est avant le début")

    def clean(self):
        if self._errors:
            return self.cleaned_data

        _ActivityCreateBaseForm.clean_interval(self.cleaned_data)
        self.check_activities()
        return self.cleaned_data

    # TODO : check for activities in same range for participants
    def check_activities(self):
        cleaned_data = self.cleaned_data
        participants = [pk for rtype, pk in cleaned_data.get('participants')]

        if cleaned_data.get('my_participation'):
            try:
                participants.append(Contact.objects.filter(is_user=cleaned_data['user']).values_list('id', flat=True)[:1][0])
            except Exception:
                pass

        _ActivityCreateBaseForm.check_activity_collisions(cleaned_data['start'], cleaned_data['end'], participants)

    @staticmethod
    def check_activity_collisions(activity_start, activity_end, participants, exclude_activity_id=None):
        collision_test = ~(Q(end__lte=activity_start) | Q(start__gte=activity_end))

        collisions = []

        for participant_id in participants:
            # find activities of participant
            activity_req = Relation.objects.filter(subject_entity__id=participant_id, type__id=REL_SUB_PART_2_ACTIVITY)

            # exclude current activity if asked
            if exclude_activity_id is not None:
                activity_req = activity_req.exclude(object_entity__id=exclude_activity_id)

            # get id of activities of participant
            activity_ids = activity_req.values_list("object_entity__id", flat=True)

            # do collision request
            #TODO: can be done with less queries ?
            #  eg:  Activity.objects.filter(relations__object_entity__id=participant_id, relations__object_entity__type__id=REL_OBJ_PART_2_ACTIVITY).filter(collision_test)
            activity_collisions = Activity.objects.filter(pk__in=activity_ids).filter(collision_test)[:1]

            if activity_collisions:
                collision = activity_collisions[0]
                participant = CremeEntity.objects.get(pk=participant_id).get_real_entity()
                #TODO: use min() and max()
                collision_start = activity_start.time() if activity_start.time() > collision.start.time() else collision.start.time()
                collision_end = activity_end.time() if activity_end.time() < collision.end.time() else collision.end.time()

                collisions.append(u"%s participe déjà à l'activité «%s» entre %s et %s." % (participant, collision, collision_start, collision_end))

        if collisions:
            raise ValidationError(collisions)

    def save(self):
        self.instance.end = self.cleaned_data['end']
        super(_ActivityCreateBaseForm, self).save()

    @staticmethod
    def save_other_participants(participants, instance):
        entity_getter = CremeEntity.objects.get

        # TODO : use content_type with Relation.create_relation_with_id_and_ct for better performance
        for relation_pk, entity_pk in participants:
            try:
                entity = entity_getter(pk=entity_pk).get_real_entity() #useful to retrieve real entity ???
                instance.add_related_entity(entity, relation_pk)
            except CremeEntity.DoesNotExist:
                pass

    @staticmethod
    def create_commercial_approach(first_entity, participants, instance):
        from datetime import datetime
        from commercial.models import CommercialApproach

        entity_getter = CremeEntity.objects.get
        ll = participants
        if first_entity:
            ll.append(('',first_entity))

        for entity_pk in ll:
            try:
                entity = entity_getter(pk=entity_pk[1]).get_real_entity()

                comapp = CommercialApproach()
                comapp.title = instance.title
                comapp.description = instance.description
                comapp.creation_date = datetime.now()
                comapp.creme_entity = entity #useful to retrieve real entity ???
                comapp.related_activity_id = instance.id
                comapp.save()
            except CremeEntity.DoesNotExist:
                pass

    def save_participants(self):
        cleaned_data = self.cleaned_data
        instance     = self.instance

        # Participant du créateur de l'event
        try:
            if cleaned_data['my_participation']:
                instance.add_related_entity(Contact.objects.filter(is_user=cleaned_data['user'])[:1][0], REL_SUB_PART_2_ACTIVITY) #?? [:1] useful ???
        except Exception, err:
            pass

        #Other participants
        participants = cleaned_data.get('participants', [])
        _ActivityCreateBaseForm.save_other_participants(participants, instance)


class ActivityCreateForm(_ActivityCreateBaseForm):
    id_entity_for_relation = IntegerField(widget=HiddenInput())
    ct_entity_for_relation = IntegerField(widget=HiddenInput())
    entity_relation_type   = CharField(widget=HiddenInput())

    entity_for_relation_preview = CharField(label=_(u'Qui / Quoi'), required=False)
    entity_relation_type_preview = ModelChoiceField(empty_label=None, queryset=RelationType.objects.none(), label=_(u"Relation avec l'activité"), required=False)

    def __init__(self, *args, **kwargs):
        super(ActivityCreateForm, self).__init__(*args, **kwargs)

        fields = self.fields
        initial_get = self.initial.get

        #TODO: use get_real_entity ????
        id_entity_for_relation = initial_get('id_entity_for_relation')
        c_entity = CremeEntity.objects.get(pk=id_entity_for_relation)
        fields['entity_for_relation_preview'].widget.attrs.update({'disabled': 'disabled', 'value':c_entity.entity_type.model_class().objects.get(pk=id_entity_for_relation)})

        initial_relation_type = RelationType.objects.filter(pk=initial_get('entity_relation_type'))
        fields['entity_relation_type_preview'].initial = initial_relation_type
        fields['entity_relation_type_preview'].queryset = initial_relation_type
        fields['entity_relation_type_preview'].widget.attrs.update({'disabled':'disabled'})

#        ActivityCreateForm.init_participants_widget(fields.get('participants'),
#                                                    [REL_SUB_ACTIVITY_SUBJECT, REL_SUB_PART_2_ACTIVITY, REL_SUB_LINKED_2_ACTIVITY])

#    @staticmethod
#    def init_participants_widget(field, predicate_ids):
#        predicates = RelationType.objects.filter(pk__in=predicate_ids).values_list('id', 'predicate')
#        field.widget.set_predicates(predicates)

    def save_participants(self):
        super(ActivityCreateForm, self).save_participants()

        cleaned_data = self.cleaned_data
        instance     = self.instance

        try:
            instance.add_related_entity(CremeEntity.objects.get(pk=cleaned_data['id_entity_for_relation']).get_real_entity(), cleaned_data["entity_relation_type"])
        except CremeEntity.DoesNotExist:
            pass

        if cleaned_data.get('is_comapp', False):
            participants = cleaned_data.get('participants', [])
            ActivityCreateForm.create_commercial_approach(cleaned_data['id_entity_for_relation'], participants, instance)


class ActivityCreateWithoutRelationForm(_ActivityCreateBaseForm):
    def __init__(self, *args, **kwargs):
        super(ActivityCreateWithoutRelationForm, self).__init__(*args, **kwargs)
        self.fields['is_comapp'].help_text = _(u"Ajoutez des participants pour qu'ils soient liés à une démarche commerciale")

    def save_participants(self):
        super(ActivityCreateWithoutRelationForm, self).save_participants()
        cleaned_data = self.cleaned_data

        if cleaned_data.get('is_comapp', False):
            participants = cleaned_data.get('participants', [])
            ActivityCreateWithoutRelationForm.create_commercial_approach(None, participants, self.instance)


#TODO: factorise ?? (ex: CreateForm inherits from EditForm....)
class ActivityEditForm(CremeModelForm):
    class Meta:
        model = Activity
        exclude = ['is_actived', 'is_deleted', 'end', 'type']

    start      = DateTimeField(label=_(u'Début'), widget=CalendarWidget())
    start_time = TimeField(label=_(u'Heure de début'), widget=TimeWidget(), required=False)
    end_time   = TimeField(label=_(u'Heure de fin'), widget=TimeWidget(), required=False)

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

        ActivityCreateForm.clean_interval(cleaned_data)

        # check if activity period change cause collisions
        participants = Relation.objects.filter(object_entity=instance, type__id=REL_SUB_PART_2_ACTIVITY).values_list("subject_entity_id", flat=True)

        ActivityCreateForm.check_activity_collisions(cleaned_data['start'], cleaned_data['end'], participants, instance.id)

        return cleaned_data

    def save(self):
        self.instance.end = self.cleaned_data['end']
        super(ActivityEditForm, self).save()

