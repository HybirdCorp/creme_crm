# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2012-2017  Hybird
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
from django.contrib.auth import get_user_model
from django.forms import ModelMultipleChoiceField  # BooleanField, ModelChoiceField
from django.utils.translation import ugettext_lazy as _, ungettext

from creme.creme_core.forms import CremeForm, MultiCreatorEntityField, MultiGenericEntityField, validators
# from creme.creme_core.forms.widgets import UnorderedMultipleChoiceWidget
from creme.creme_core.models import RelationType, Relation

from creme.persons import get_contact_model

from .. import constants
from ..models import Calendar
from ..utils import check_activity_collisions
from .fields import UserParticipationField


logger = logging.getLogger(__name__)
Contact = get_contact_model()


class ParticipantCreateForm(CremeForm):
    # my_participation    = BooleanField(required=False, initial=False,
    #                                    label=_(u'Do I participate to this activity?'),
    #                                   )
    # my_calendar         = ModelChoiceField(queryset=Calendar.objects.none(),
    #                                        required=False, empty_label=None,
    #                                        label=_(u'On which of my calendar this activity will appear?'),
    #                                       )
    my_participation    = UserParticipationField(label=_(u'Do I participate to this activity?'), empty_label=None)
    participating_users = ModelMultipleChoiceField(label=_(u'Other participating users'),
                                                   queryset=get_user_model().objects.filter(is_staff=False),
                                                   required=False,
                                                   # widget=UnorderedMultipleChoiceWidget,
                                                  )
    participants        = MultiCreatorEntityField(label=_(u'Participants'), model=Contact, required=False)

    def __init__(self, entity, *args, **kwargs):
        super(ParticipantCreateForm, self).__init__(*args, **kwargs)
        self.activity = entity
        self.participants = set()

        user = self.user
        user_pk = user.pk
        fields = self.fields

        existing = Contact.objects.filter(relations__type=constants.REL_SUB_PART_2_ACTIVITY,
                                          relations__object_entity=entity.id,
                                         )

        participants_field = fields['participants']
        participants_field.q_filter = {'~pk__in': [c.id for c in existing],
                                       'is_user__isnull': True,
                                      }
        participants_field.force_creation = True  # TODO: in constructor ?

        if entity.is_auto_orga_subject_enabled():
            participants_field.help_text = _(u'The organisations of the participants will '
                                             u'be automatically added as subjects'
                                            )

        existing_users = [c.is_user.pk for c in existing if c.is_user]
        user_qs = get_user_model().objects.filter(is_staff=False) \
                                          .exclude(pk__in=existing_users) \
                                          .exclude(pk=user_pk)

        fields['participating_users'].queryset = user_qs
        if not user_qs:
            fields['participating_users'].widget.attrs = {'reduced': 'true'}

        if user_pk in existing_users:
            del fields['my_participation']
            # del fields['my_calendar']
        # else:
        #     fields['my_participation'].widget.attrs['onclick'] = \
        #         "if($(this).is(':checked')){$('#id_my_calendar').removeAttr('disabled');}else{$('#id_my_calendar').attr('disabled', 'disabled');}"
        #
        #     my_calendar_field = fields['my_calendar']
        #     my_calendar_field.queryset = Calendar.objects.filter(user=user)
        #     my_calendar_field.widget.attrs['disabled'] = True

    # def clean_participants(self):
    #     return validate_linkable_entities(self.cleaned_data['participants'], self.user)

    def clean_participating_users(self):
        users = set()

        for user in self.cleaned_data['participating_users']:
            if not user.is_team:
                users.add(user)
            else:
                users.update(user.teammates.itervalues())

        return validators.validate_linkable_entities(Contact.objects.filter(is_user__in=users),
                                                     self.user,
                                                    )

    # TODO: factorise with ActivityCreateForm
    def clean_my_participation(self):
        # my_participation = self.cleaned_data.get('my_participation', False)
        my_participation = self.cleaned_data['my_participation']

        # if my_participation:
        if my_participation[0]:
            user = self.user
            self.participants.add(validators.validate_linkable_entity(user.linked_contact, user))

        return my_participation

    def clean(self):
        cleaned_data = super(ParticipantCreateForm, self).clean()

        if not self._errors:
            activity = self.activity
            extend_participants = self.participants.update
            extend_participants(cleaned_data['participating_users'])
            extend_participants(cleaned_data['participants'])

            # if cleaned_data.get('my_participation') and not cleaned_data.get('my_calendar'):
            #     self.add_error('my_calendar', _(u'If you participate, you have to choose one of your calendars.'))

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
                                  type_id=constants.REL_SUB_PART_2_ACTIVITY, user=activity.user,
                                 )
        me = self.user

        for participant in self.participants:
            user = participant.is_user
            if user:
                # activity.calendars.add(self.cleaned_data['my_calendar'] if user == me else
                activity.calendars.add(self.cleaned_data['my_participation'][1] if user == me else
                                       Calendar.get_user_default_calendar(user)
                                      )

            create_relation(subject_entity=participant)


class SubjectCreateForm(CremeForm):
    # TODO: qfilter to exclude current subjects, see MultiGenericEntityField
    subjects = MultiGenericEntityField(label=_(u'Subjects'))

    def __init__(self, entity, *args, **kwargs):
        super(SubjectCreateForm, self).__init__(*args, **kwargs)
        self.activity = entity
        self.rtype = rtype = RelationType.objects.get(pk=constants.REL_SUB_ACTIVITY_SUBJECT)
        ctypes = rtype.subject_ctypes.all()
        subjects_f = self.fields['subjects']
        subjects_f.allowed_models = [ct.model_class() for ct in ctypes]
        subjects_f.initial = [[(ctypes[0].pk, None)]]

    def clean_subjects(self):
        subjects = self.cleaned_data['subjects']

        # TODO: remove when the field manage 'qfilter'
        already_subjects = {r.object_entity_id
                                for r in self.activity.get_subject_relations(real_entities=False)
                           }
        duplicates = [subject for subject in subjects if subject.id in already_subjects]

        if duplicates:
            raise ValidationError(ungettext(u'This entity is already a subject: %(duplicates)s',
                                            u'These entities are already subjects: %(duplicates)s',
                                            len(duplicates)
                                           ),
                                  params={'duplicates': u', '.join(unicode(e) for e in duplicates)},
                                 )

        # return validate_linkable_entities(subjects, self.user)
        return subjects

    def save(self):
        create_relation = partial(Relation.objects.create, type=self.rtype,
                                  object_entity=self.activity, user=self.user,
                                 )

        for entity in self.cleaned_data['subjects']:
            create_relation(subject_entity=entity)
