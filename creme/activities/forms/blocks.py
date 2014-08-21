# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2012-2014  Hybird
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
import logging

from django.core.exceptions import ValidationError
from django.forms import BooleanField, ModelChoiceField, ModelMultipleChoiceField
from django.forms.util import ErrorList
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.auth.models import User

from creme.creme_core.forms import CremeForm
from creme.creme_core.forms.fields import MultiCreatorEntityField, MultiGenericEntityField
from creme.creme_core.forms.validators import validate_linkable_entities, validate_linkable_entity
from creme.creme_core.forms.widgets import UnorderedMultipleChoiceWidget
from creme.creme_core.models import RelationType, Relation

from creme.persons.models import Contact

from ..constants import *
from ..models import Calendar
from ..utils import check_activity_collisions


logger = logging.getLogger(__name__)


class ParticipantCreateForm(CremeForm):
    my_participation    = BooleanField(required=False, initial=False,
                                       label=_(u"Do I participate to this activity?"),
                                      )
    my_calendar         = ModelChoiceField(queryset=Calendar.objects.none(),
                                           required=False, empty_label=None,
                                           label=_(u"On which of my calendar this activity will appear?"),
                                          )
    participating_users = ModelMultipleChoiceField(label=_(u'Other participating users'),
                                                   queryset=User.objects.filter(is_staff=False),
                                                   required=False, widget=UnorderedMultipleChoiceWidget,
                                                  )
    participants        = MultiCreatorEntityField(label=_(u'Participants'), model=Contact, required=False)

    def __init__(self, entity, *args, **kwargs):
        super(ParticipantCreateForm, self).__init__(*args, **kwargs)

        self.activity = entity
        self.participants = []

        user = self.user
        user_pk = user.pk
        fields = self.fields

        existing = Contact.objects.filter(relations__type=REL_SUB_PART_2_ACTIVITY,
                                          relations__object_entity=entity.id,
                                         )

        participants_field = fields['participants']
        participants_field.q_filter = {'~pk__in': [c.id for c in existing],
                                       'is_user__isnull': True,
                                      }
        if entity.is_auto_orga_subject_enabled():
            participants_field.help_text = ugettext('The organisations of the participants will be automatically added as subjects')

        existing_users = [c.is_user.pk for c in existing if c.is_user]
        user_qs = User.objects.filter(is_staff=False) \
                              .exclude(pk__in=existing_users) \
                              .exclude(pk=user_pk)

        fields['participating_users'].queryset = user_qs
        if not user_qs:
            fields['participating_users'].widget.attrs = {'reduced': 'true'}

        if user_pk in existing_users:
            del fields['my_participation']
            del fields['my_calendar']
        else:
            #TODO: refactor this with a smart widget that manages dependencies
            fields['my_participation'].widget.attrs['onclick'] = \
                "if($(this).is(':checked')){$('#id_my_calendar').removeAttr('disabled');}else{$('#id_my_calendar').attr('disabled', 'disabled');}"

            my_calendar_field = fields['my_calendar']
            my_calendar_field.queryset = Calendar.objects.filter(user=user)
            my_calendar_field.widget.attrs['disabled'] = True #TODO: remove when dependencies system is OK

    def clean_participants(self):
        return validate_linkable_entities(self.cleaned_data['participants'], self.user)

    def clean_participating_users(self):
        return validate_linkable_entities(Contact.objects.filter(is_user__in=self.cleaned_data['participating_users']),
                                          self.user,
                                         )

    #TODO: factorise with ActivityCreateForm
    def clean_my_participation(self):
        my_participation = self.cleaned_data.get('my_participation', False)

        if my_participation:
            user = self.user

            #try:
                #user_contact = Contact.objects.get(is_user=user)
            #except Contact.DoesNotExist:
                #logger.warn('No Contact linked to this user: %s', user)
            #else:
                #self.participants.append(validate_linkable_entity(user_contact, user))
            self.participants.append(validate_linkable_entity(user.linked_contact, user))

        return my_participation

    def clean(self):
        cleaned_data = super(ParticipantCreateForm, self).clean()

        if not self._errors:
            activity = self.activity
            extend_participants = self.participants.extend
            extend_participants(cleaned_data['participating_users'])
            extend_participants(cleaned_data['participants'])

            if cleaned_data.get('my_participation') and not cleaned_data.get('my_calendar'):
                self.errors['my_calendar'] = ErrorList([ugettext(u"If you participe, you have to choose one of your calendars.")])

            collisions = check_activity_collisions(activity.start, activity.end,
                                                   self.participants, busy=activity.busy,
                                                   exclude_activity_id=activity.id,
                                                  )
            if collisions:
                raise ValidationError(collisions)

        return cleaned_data

    def save(self):
        activity = self.activity

        create_relation = partial(Relation.objects.create, object_entity=activity,
                                  type_id=REL_SUB_PART_2_ACTIVITY, user=activity.user
                                 )

        for participant in self.participants:
            user = participant.is_user
            if user:
                activity.calendars.add(self.cleaned_data['my_calendar'] if user == self.user else
                                       Calendar.get_user_default_calendar(user)
                                      )

            create_relation(subject_entity=participant)


class SubjectCreateForm(CremeForm):
    subjects = MultiGenericEntityField(label=_(u'Subjects')) #TODO: qfilter to exclude current subjects, see MultiGenericEntityField

    def __init__(self, entity, *args, **kwargs):
        super(SubjectCreateForm, self).__init__(*args, **kwargs)
        self.activity = entity
        self.rtype = rtype = RelationType.objects.get(pk=REL_SUB_ACTIVITY_SUBJECT)
        self.fields['subjects'].allowed_models = [ct.model_class() for ct in rtype.subject_ctypes.all()]

    def clean_subjects(self):
        return validate_linkable_entities(self.cleaned_data['subjects'], self.user)

    def save(self):
        create_relation = partial(Relation.objects.create, type=self.rtype,
                                  object_entity=self.activity, user=self.user,
                                 )

        for entity in self.cleaned_data['subjects']:
            create_relation(subject_entity=entity)
