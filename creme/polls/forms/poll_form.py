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

# import warnings
from itertools import chain, zip_longest

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms import CremeForm, CremeModelForm  # CremeEntityForm
from creme.creme_core.forms.fields import ListEditionField
from creme.creme_core.forms.widgets import CremeRadioSelect
from creme.creme_core.utils import find_first, update_model_instance

# from .. import get_pollform_model
from ..core import PollLineType
from ..models import PollFormLine, PollFormLineCondition, PollFormSection
from ..utils import SectionTree
from .fields import PollFormLineConditionsField

# class PollFormForm(CremeEntityForm):
#     class Meta(CremeEntityForm.Meta):
#         model = get_pollform_model()
#
#     def __init__(self, *args, **kwargs):
#         warnings.warn('PollFormForm is deprecated.', DeprecationWarning)
#         super().__init__(*args, **kwargs)


class PollFormSectionEditForm(CremeModelForm):
    class Meta(CremeModelForm.Meta):
        model = PollFormSection

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pform = entity


class PollFormSectionCreateForm(PollFormSectionEditForm):
    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent = parent

    def save(self, *args, **kwargs):
        instance = self.instance
        pform = self.pform
        instance.pform = pform

        parent = self.parent
        instance.parent = parent

        # Order management -----------------------------------------------------
        # The section after the one we create : their order have to be incremented
        next_sections = []
        parent_id = parent.id if parent else None

        for section in PollFormSection.objects.order_by('-order'):
            if section.parent_id == parent_id or section.id == parent_id:
                order = section.order + 1
                break

            next_sections.append(section)
        else:
            order = 1
        # ----------------------------------------------------------------------

        instance.order = order

        for section in next_sections:
            section.order += 1
            section.save()

        return super().save(*args, **kwargs)


class _PollFormLineForm(CremeModelForm):
    class Meta(CremeModelForm.Meta):
        model = PollFormLine

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pform = entity


# TODO: get the fields from PollLineTypes objects ???
class PollFormLineCreateForm(_PollFormLineForm):
    type = forms.TypedChoiceField(
        label=_('Type'),
        choices=PollLineType.choices(),
        coerce=int,
        initial=PollLineType.STRING,
    )
    lower_bound = forms.IntegerField(
        label=_('Lower bound'),
        required=False,
        help_text=_('For integer type only.'),
    )
    upper_bound = forms.IntegerField(
        label=_('Upper bound'),
        required=False,
        help_text=_('For integer type only.'),
    )
    choices = forms.CharField(
        widget=forms.Textarea,
        label=_('Available choices'),
        required=False,
        help_text=_(
            'Give the possible choices (one per line) '
            'if you choose the type "Choice list".'
        ),
    )

    def __init__(self, section=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.section = section

        # Lines which are in the section where we create our line.
        self.section_lines = section_lines = []

        # The lines after the one we create (but not in the same section):
        # their order have to be incremented
        self.next_lines = next_lines = []

        # Order of the last line before our section (used if our section is empty).
        self.empty_section_order = 1

        nodes = [*SectionTree(self.pform)]
        section_id = section.id if section else None

        # Filling of 'section_lines' & 'next_lines'
        node_it = reversed(nodes)
        try:
            while True:
                node = next(node_it)

                if not node.is_section:
                    if node.section_id == section_id:
                        section_lines.append(node)
                    else:
                        next_lines.append(node)
                elif node.id == section_id:
                    previous_line = find_first(node_it, (lambda node: not node.is_section), None)

                    if previous_line:
                        self.empty_section_order = previous_line.order + 1

                    break
        except StopIteration:
            pass

        if section_lines:
            section_lines.reverse()

            # TODO: cached_gettext ??
            msg_fmt = gettext('Before: «{question}» (#{number})').format
            choices = [
                (0, gettext('Start of section')),
                *(
                    (i, msg_fmt(question=node.question, number=node.number))
                    for i, node in enumerate(section_lines[1:], start=1)
                ),
                (len(section_lines), gettext('End of section')),
            ]

            self.fields['index'] = forms.TypedChoiceField(
                label=gettext('Order'),
                coerce=int,
                choices=choices,
                initial=len(choices) - 1,
            )

    def clean(self):
        cleaned_data = super().clean()

        if not self._errors:
            get_data = cleaned_data.get
            self.type_args = PollLineType.build_serialized_args(
                ptype=cleaned_data['type'],
                lower_bound=get_data('lower_bound'),
                upper_bound=get_data('upper_bound'),
                choices=[
                    *enumerate(
                        filter(
                            None,
                            (choice.strip() for choice in get_data('choices', '').split('\n'))
                        ),
                        start=1,
                    )
                ],
            )  # Can raise Validation errors

        return cleaned_data

    def save(self, *args, **kwargs):
        cdata = self.cleaned_data
        section_lines = self.section_lines

        if not section_lines:
            index = 0
            order = self.empty_section_order
        else:
            index = cdata['index']

            if index < len(section_lines):
                order = section_lines[index].order
            else:
                order = section_lines[-1].order + 1

        instance = self.instance
        instance.pform     = self.pform
        instance.section   = self.section
        instance.order     = order
        instance.type      = cdata['type']
        instance.type_args = self.type_args

        for line in chain(section_lines[index:], self.next_lines):
            line.order += 1
            line.save()

        return super().save(*args, **kwargs)


class PollFormLineEditForm(_PollFormLineForm):
    class Meta(_PollFormLineForm.Meta):
        exclude = ('type',)

    error_messages = {
        'empty_choices': _('Choices can not be empty.'),
        'used_choice': _(
            'You can not delete the choice "%(choice)s" because it '
            'is used in a condition by the question "%(question)s".'
        ),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial_choices = None
        choices = self.instance.poll_line_type.get_editable_choices()

        if choices is not None:
            fields = self.fields
            self.initial_choices = choices
            fields['old_choices'] = ListEditionField(
                content=[c[1] for c in choices],
                label=gettext('Existing choices'),
                help_text=gettext('Uncheck the choices you want to delete.'),
            )
            fields['new_choices'] = forms.CharField(
                widget=forms.Textarea,
                required=False,
                label=gettext('New choices of the list'),
                help_text=gettext('Give the new possible choices (one per line).')
            )

    def clean_old_choices(self):
        old_choices = self.cleaned_data['old_choices']
        self.choices_2_keep = choices_2_keep = []
        self.choices_2_del = choices_2_del = []

        for existing_choice, choice in zip(self.initial_choices, old_choices):
            if choice is None:
                choices_2_del.append(existing_choice)
            else:
                choice = choice.strip()

                if not choice:
                    raise ValidationError(
                        self.error_messages['empty_choices'],
                        code='empty_choices',
                    )  # TODO: move this validation to the field ??

                choices_2_keep.append((existing_choice[0], choice))

        if choices_2_del:
            condition = PollFormLineCondition.objects.filter(
                source=self.instance,
                raw_answer__in=[str(c[0]) for c in choices_2_del],
            ).first()

            if condition is not None:
                choice_id = int(condition.raw_answer)

                raise ValidationError(
                    self.error_messages['used_choice'],
                    params={
                        'choice': find_first(
                            choices_2_del,
                            (lambda c: c[0] == choice_id)
                        )[1],
                        'question': condition.line.question,
                    },
                    code='used_choice',
                )

        return old_choices

    def clean(self):
        cleaned_data = super().clean()
        self.type_args = None

        if not self._errors and self.initial_choices:
            choices_2_del = [
                # TODO cache poll_line_type (in line ?)
                *self.instance.poll_line_type.get_deleted_choices(),
                *self.choices_2_del,
            ]

            choices_2_keep = self.choices_2_keep
            # TODO: factorise ---> in a new field 'MultipleCharField'
            choices_2_keep.extend(
                enumerate(
                    filter(
                        None,
                        (
                            choice.strip()
                            for choice in cleaned_data.get('new_choices', '').split('\n')
                        )
                    ),
                    start=len(choices_2_keep) + len(choices_2_del) + 1,
                )
            )

            self.type_args = PollLineType.build_serialized_args(
                ptype=self.instance.type,
                choices=choices_2_keep,
                del_choices=choices_2_del,
            )  # Can raise Validation errors

        return cleaned_data

    def save(self, *args, **kwargs):
        if self.type_args:
            self.instance.type_args = self.type_args

        return super().save(*args, **kwargs)


class PollFormLineConditionsForm(CremeForm):
    use_or = forms.TypedChoiceField(
        label=_('Use OR or AND between conditions'),
        choices=[(0, _('AND')), (1, _('OR'))],
        coerce=(lambda x: bool(int(x))),
        widget=CremeRadioSelect,
    )
    conditions = PollFormLineConditionsField(label=_('Conditions'), required=False)

    def __init__(self, entity, line, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.line = line
        self.old_conditions = conditions = line.get_conditions()

        fields = self.fields
        # TODO: remove 'bool' if no more nullable
        fields['use_or'].initial = int(bool(line.conds_use_or))

        conditions_f = fields['conditions']
        conditions_f.sources = entity.lines.filter(order__lt=line.order)
        conditions_f.initial = conditions

    def save(self, *args, **kwargs):
        line = self.line
        cdata = self.cleaned_data

        update_model_instance(line, conds_use_or=cdata['use_or'])

        conds2del = []

        # TODO: select for update ??
        for old_condition, condition in zip_longest(self.old_conditions, cdata['conditions']):
            if not condition:
                # Less new conditions that old conditions => delete conditions in excess
                conds2del.append(old_condition.id)
            elif not old_condition:
                condition.line = line
                condition.save()
            elif old_condition.update(condition):
                old_condition.save()

        if conds2del:
            PollFormLineCondition.objects.filter(pk__in=conds2del).delete()
