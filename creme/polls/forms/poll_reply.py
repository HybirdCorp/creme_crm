################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2012-2025  Hybird
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

from itertools import repeat

from django import forms
from django.core.exceptions import ValidationError
from django.http import Http404
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

import creme.creme_core.forms.base as core_forms
import creme.creme_core.forms.fields as core_fields
from creme import persons, polls
from creme.creme_config.forms.fields import CreatorEnumerableModelChoiceField
from creme.creme_core.auth import EntityCredentials
from creme.creme_core.gui.bulk_update import FieldOverrider
from creme.creme_core.models import FieldsConfig

Contact      = persons.get_contact_model()
Organisation = persons.get_organisation_model()
PollCampaign = polls.get_pollcampaign_model()
PollForm     = polls.get_pollform_model()
PollReply    = polls.get_pollreply_model()


class PollRepliesCreationForm(core_forms.CremeForm):
    user = CreatorEnumerableModelChoiceField(model=PollReply, field_name='user')
    name = forms.CharField(label=_('Name'))
    campaign = core_fields.CreatorEntityField(
        label=pgettext_lazy('polls', 'Related campaign'),
        model=PollCampaign, required=False,
    )
    number = forms.IntegerField(
        label=_('Number of replies'), initial=1, min_value=1, required=False,
    )
    persons = core_fields.MultiGenericEntityField(
        label=_('Persons who filled'), required=False,
        models=[Organisation, Contact],
        help_text=_(
            'Each reply will be linked to a person '
            '(and "Number of replies" will be ignored)'
        ),
    )
    pform = core_fields.CreatorEntityField(
        label=_('Related form'), model=polls.get_pollform_model(),
    )

    def __init__(self, entity=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.preplies = []
        fields = self.fields
        fields['user'].initial = self.user.id

        if entity is not None:
            if isinstance(entity, PollCampaign):
                del fields['campaign']
                self.campaign = entity
            elif isinstance(entity, PollForm):
                del fields['pform']
                self._set_pform_n_validate(entity, Http404)
            elif isinstance(entity, Contact | Organisation):
                del fields['persons']
                del fields['number']
                self.persons = [entity]

    def clean_campaign(self):
        self.campaign = campaign = self.cleaned_data['campaign']

        return campaign

    def clean_number(self):
        return self.cleaned_data['number'] or 1

    def clean_persons(self):
        self.persons = linked_persons = self.cleaned_data['persons']

        return linked_persons

    def clean_pform(self):
        pform = self.cleaned_data['pform']
        self._set_pform_n_validate(pform, ValidationError)

        return pform

    def _set_pform_n_validate(self, pform, exception_class):
        lines = pform.lines.filter(disabled=False)

        if not lines:
            raise exception_class(gettext('The form must contain one line at least.'))

        self.pform = pform
        self.pform_lines = lines

    # Easy to hook it in another app -> do not save
    def create_preply(self, index, person, total_number):
        cleaned_data = self.cleaned_data
        name = cleaned_data['name']

        if total_number != 1:
            name += f'#{index}'

        return PollReply(
            user=cleaned_data['user'], pform=self.pform,
            type=self.pform.type, name=name,
            campaign=self.campaign, person=person,
        )

    def save(self, *args, **kwargs):
        linked_persons = self.persons

        if linked_persons:
            reply_number = len(linked_persons)
            linked_persons = linked_persons
        else:
            reply_number = self.cleaned_data['number']
            linked_persons = repeat(None, reply_number)

        duplicate_tree = self.pform.duplicate_tree

        for i, person in enumerate(linked_persons, start=1):
            instance = self.create_preply(i, person, reply_number)
            instance.save()
            duplicate_tree(instance, self.pform_lines)
            self.preplies.append(instance)


class PollReplyEditionForm(core_forms.CremeEntityForm):
    # TODO: rename it 'person' when initial works well + remove from exclude + remove save()
    related_person = core_fields.GenericEntityField(
        label=_('Person who filled'),
        required=False,
        models=[Organisation, Contact],
    )

    class Meta:
        model = PollReply
        exclude = ('pform', 'person')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['related_person'].initial = self.instance.person

    def save(self, *args, **kwargs):
        self.instance.person = self.cleaned_data['related_person']
        return super().save(*args, **kwargs)


class PersonAddRepliesForm(core_forms.CremeForm):
    # TODO: qfilter to exclude linked replies ??
    replies = core_fields.MultiCreatorEntityField(
        label=_('Replies'), model=polls.get_pollreply_model(),
        credentials=EntityCredentials.CHANGE,
    )

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.person = entity

    def save(self, *args, **kwargs):
        for reply in self.cleaned_data['replies']:
            reply.person = self.person
            reply.save()


class PollReplyFillForm(core_forms.CremeForm):
    question = core_fields.ReadonlyMessageField(label=_('Question'), initial='??')

    def __init__(self, line_node, instance=None, *args, **kwargs):
        "@param line_node Node (see ReplySectionTree) related to a PollReplyLine."
        super().__init__(*args, **kwargs)
        self.poll_reply = instance
        self.line_node = line_node

        fields = self.fields
        number = line_node.number
        question_f = fields['question']

        if number:
            # TODO: use NodeStyle ??
            question_f.initial = f'{number} - {line_node.question}'
            fields['not_applicable'] = forms.BooleanField(
                label=gettext('Not applicable'),
                required=False,
                initial=not line_node.applicable,
            )
        else:
            question_f.label = _('Comment')
            question_f.initial = line_node.question

        answer_field = line_node.answer_formfield
        if answer_field is not None:
            # TODO: set dynamically "required" on client side with the value of 'not_applicable'
            answer_field.required = answer_field.widget.is_required = False
            fields['answer'] = answer_field

    def clean(self):
        cdata = super().clean()
        errors = self._errors

        if (
            not errors
            and not cdata.get('not_applicable', False)
            and self.line_node.poll_line_type.editable
            and cdata.get('answer') is None
        ):
            errors['answer'] = self.error_class([gettext('The answer is required.')])

        return cdata

    def save(self, *args, **kwargs):
        line = self.line_node
        cdata = self.cleaned_data
        not_applicable = cdata.get('not_applicable', False)

        if not_applicable:
            answer = None
        elif line.poll_line_type.editable:
            answer = cdata['answer']
        else:
            answer = ''

        line.applicable = not not_applicable
        line.answer = answer

        line.save()

        return self.poll_reply


class PersonOverrider(FieldOverrider):
    field_names = ['person']

    def formfield(self, instances, user, **kwargs):
        first = instances[0]
        person_field = core_fields.GenericEntityField(
            label=_('Person who filled'),
            required=FieldsConfig.objects
                                 .get_for_model(type(first))
                                 .is_fieldname_required(self.field_names[0]),
            models=[Organisation, Contact],
            user=user,
        )

        if len(instances) == 1:
            person_field.initial = first.person

        return person_field

    def post_clean_instance(self, *, instance, value, form):
        # TODO: default implementation?
        setattr(instance, self.field_names[0], value)
