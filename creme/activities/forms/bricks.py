# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2012-2021  Hybird
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
from functools import partial

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models.query_utils import Q
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from creme.creme_core.forms import (
    CremeForm,
    MultiCreatorEntityField,
    MultiGenericEntityField,
)
from creme.creme_core.models import Relation, RelationType
from creme.creme_core.utils.chunktools import iter_as_chunk
from creme.persons import get_contact_model

from .. import constants
from ..models import Calendar
from ..utils import check_activity_collisions, is_auto_orga_subject_enabled
from . import fields as act_fields

logger = logging.getLogger(__name__)
Contact = get_contact_model()


class ParticipantCreateForm(CremeForm):
    my_participation = act_fields.UserParticipationField(
        label=_('Do I participate to this activity?'), empty_label=None,
    )
    participating_users = act_fields.ParticipatingUsersField(
        label=_('Other participating users'), required=False,
    )
    participants = MultiCreatorEntityField(
        label=_('Participants'), model=Contact, required=False,
    )

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.activity = entity
        self.participants = set()

        user = self.user
        user_pk = user.pk
        fields = self.fields

        existing = Contact.objects.filter(
            relations__type=constants.REL_SUB_PART_2_ACTIVITY,
            relations__object_entity=entity.id,
        )

        participants_field = fields['participants']
        participants_field.q_filter = (
            ~Q(pk__in=[c.id for c in existing]) & Q(is_user__isnull=True)
        )
        participants_field.force_creation = True  # TODO: in constructor ?

        if is_auto_orga_subject_enabled():
            participants_field.help_text = _(
                'The organisations of the participants will '
                'be automatically added as subjects'
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

    # TODO: factorise with ActivityCreateForm
    def clean_my_participation(self):
        my_participation = self.cleaned_data['my_participation']

        if my_participation[0]:
            self.participants.add(self.user.linked_contact)

        return my_participation

    def clean(self):
        cleaned_data = super().clean()

        if not self._errors:
            activity = self.activity
            extend_participants = self.participants.update
            extend_participants(cleaned_data['participating_users'])
            extend_participants(cleaned_data['participants'])

            collisions = check_activity_collisions(
                activity.start, activity.end,
                self.participants,
                busy=activity.busy,
                exclude_activity_id=activity.id,
            )
            if collisions:
                raise ValidationError(collisions)

        return cleaned_data

    def save(self):
        activity = self.activity
        create_relation = partial(
            Relation.objects.safe_create,
            object_entity=activity,
            type_id=constants.REL_SUB_PART_2_ACTIVITY,
            user=activity.user,
        )
        me = self.user
        other_users = []
        calendars = []

        for participant in self.participants:
            user = participant.is_user
            if user:
                if user == me:
                    calendars.append(self.cleaned_data['my_participation'][1])
                else:
                    other_users.append(user)

            create_relation(subject_entity=participant)

        calendars.extend(Calendar.objects.get_default_calendars(other_users).values())
        for calendars_chunk in iter_as_chunk(calendars, 256):
            activity.calendars.add(*calendars_chunk)


class SubjectCreateForm(CremeForm):
    # TODO: qfilter to exclude current subjects, see MultiGenericEntityField
    subjects = MultiGenericEntityField(label=_('Subjects'))

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.activity = entity
        self.rtype = rtype = RelationType.objects.get(pk=constants.REL_SUB_ACTIVITY_SUBJECT)
        ctypes = rtype.subject_ctypes.all()
        subjects_f = self.fields['subjects']
        subjects_f.allowed_models = [ct.model_class() for ct in ctypes]
        subjects_f.initial = [[(ctypes[0].pk, None)]]

    def clean_subjects(self):
        subjects = self.cleaned_data['subjects']

        # TODO: remove when the field manage 'qfilter'
        already_subjects = {
            r.object_entity_id
            for r in self.activity.get_subject_relations(real_entities=False)
        }
        duplicates = [subject for subject in subjects if subject.id in already_subjects]

        if duplicates:
            raise ValidationError(
                ngettext(
                    'This entity is already a subject: %(duplicates)s',
                    'These entities are already subjects: %(duplicates)s',
                    len(duplicates),
                ),
                params={'duplicates': ', '.join(str(e) for e in duplicates)},
            )

        return subjects

    def save(self):
        create_relation = partial(
            Relation.objects.safe_create,
            type=self.rtype, object_entity=self.activity, user=self.user,
        )

        for entity in self.cleaned_data['subjects']:
            create_relation(subject_entity=entity)
