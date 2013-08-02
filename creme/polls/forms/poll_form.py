# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2012-2013  Hybird
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

from itertools import izip, chain

from django.core.exceptions import ValidationError
from django.forms.fields import IntegerField, CharField, TypedChoiceField
from django.forms.widgets import Textarea
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.forms import CremeForm, CremeModelForm, CremeEntityForm
from creme.creme_core.forms.fields import ListEditionField
from creme.creme_core.utils import find_first, update_model_instance

from ..core import  PollLineType
from ..models import PollForm, PollFormSection, PollFormLine, PollFormLineCondition
from ..utils import SectionTree
from .fields import PollFormLineConditionsField


class PollFormForm(CremeEntityForm):
    class Meta:
        model = PollForm


class PollFormSectionEditForm(CremeModelForm):
    class Meta:
        model = PollFormSection

    def __init__(self, entity, *args, **kwargs):
        super(PollFormSectionEditForm, self).__init__(*args, **kwargs)
        self.pform = entity


class PollFormSectionCreateForm(PollFormSectionEditForm):
    def save(self, *args, **kwargs):
        instance = self.instance
        pform = self.pform
        instance.pform = pform

        parent = self.initial.get('parent')
        instance.parent = parent

        # order management -----------------------------------------------------
        next_sections = [] #the section after the one we create : their order have to be incremented
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

        return super(PollFormSectionCreateForm, self).save(*args, **kwargs)


class _PollFormLineForm(CremeModelForm):
    class Meta:
        model = PollFormLine

    def __init__(self, entity, *args, **kwargs):
        super(_PollFormLineForm, self).__init__(*args, **kwargs)
        self.pform = entity


#TODO: get the fields from PollLineTypes objects ???
class PollFormLineCreateForm(_PollFormLineForm):
    type        = TypedChoiceField(label=_(u'Type'), choices=PollLineType.choices(),
                                   coerce=int, initial=PollLineType.STRING
                                  )
    lower_bound = IntegerField(label=_(u'Lower bound'), required=False,
                               help_text=_(u'For integer type only.')
                              )
    upper_bound = IntegerField(label=_(u'Upper bound'), required=False,
                               help_text=_(u'For integer type only.')
                              )
    choices     = CharField(widget=Textarea(), label=_(u'List of choices'), required=False,
                            help_text=_(u'Give the possible choices (one per line) if you choose the type "Choices list".')
                           )

    def __init__(self, *args, **kwargs):
        super(PollFormLineCreateForm, self).__init__(*args, **kwargs)
        self.section = section = self.initial.get('section')
        self.section_lines = section_lines = [] #lines which are in the section where we create our line
        self.next_lines = next_lines = [] #the lines after the one we create (but not in the same section): their order have to be incremented
        self.empty_section_order = 1 #order of the last line before our section (used if our section is empty)

        nodes = list(SectionTree(self.pform))
        section_id = section.id if section else None

        # Filling of 'section_lines' & 'next_lines'
        node_it = reversed(nodes)
        try:
            while True:
                node = node_it.next()

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

            choices = [(0, ugettext(u'Start of section'))]
            msg_fmt = ugettext(u'Before: «%(question)s» (#%(number)s)') #TODO: cached_ugettext ??

            choices.extend((i, msg_fmt % {'question': node.question, 'number': node.number})
                                for i, node in enumerate(section_lines[1:], start=1)
                          )
            choices.append((len(section_lines), ugettext(u'End of section')))

            self.fields['index'] = TypedChoiceField(label=ugettext('Order'), coerce=int,
                                                    choices=choices, initial=len(choices) - 1
                                                   )

    def clean(self):
        cleaned_data = self.cleaned_data

        if not self._errors:
            get_data = cleaned_data.get
            self.type_args = PollLineType.build_serialized_args(ptype=cleaned_data['type'],
                                                                lower_bound=get_data('lower_bound'),
                                                                upper_bound=get_data('upper_bound'),
                                                                choices=list(enumerate(filter(None,
                                                                                              (choice.strip() for choice in get_data('choices', '').split('\n'))
                                                                                             ),
                                                                                       start=1
                                                                                      )
                                                                            ),
                                                               ) #can raise Validation errors

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

        return super(PollFormLineCreateForm, self).save(*args, **kwargs)


class PollFormLineEditForm(_PollFormLineForm):
    class Meta(_PollFormLineForm.Meta):
        exclude = ('type',)

    def __init__(self, *args, **kwargs):
        super(PollFormLineEditForm, self).__init__(*args, **kwargs)
        if self.instance.disabled:  #TODO: improve the generic view edit_related_to_entity instead....
            from django.http import Http404
            raise Http404('You can not edit a disabled line.')

        self.initial_choices = None
        choices = self.instance.poll_line_type.get_editable_choices()

        if choices is not None:
            fields = self.fields
            self.initial_choices = choices
            fields['old_choices'] = ListEditionField(content=[c[1] for c in choices],
                                                     label=ugettext(u'Existing choices'),
                                                     help_text=ugettext(u'Uncheck the choices you want to delete.'),
                                                    )
            fields['new_choices'] = CharField(widget=Textarea(), required=False,
                                              label=ugettext(u'New choices of the list'),
                                              help_text=ugettext(u'Give the new possible choices (one per line).')
                                             )

    def clean_old_choices(self):
        old_choices = self.cleaned_data['old_choices']
        self.choices_2_keep = choices_2_keep = []
        self.choices_2_del = choices_2_del = []

        for existing_choice, choice in izip(self.initial_choices, old_choices):
            if choice is None:
                choices_2_del.append(existing_choice)
            else:
                choice = choice.strip()

                if not choice:
                    raise ValidationError(ugettext('Choices can not be empty.')) #TODO: move this validation to the field ??

                choices_2_keep.append((existing_choice[0], choice))

        if choices_2_del:
            conditions = PollFormLineCondition.objects.filter(source=self.instance,
                                                              raw_answer__in=[str(c[0]) for c in choices_2_del],
                                                             )[:1]

            if conditions:
                condition = conditions[0]
                choice_id = int(condition.raw_answer)

                raise ValidationError(ugettext('You can not delete the choice "%(choice)s" because it is '
                                               'used in a condition by the question "%(question)s".') % {
                                            'choice':   find_first(choices_2_del, (lambda c: c[0] == choice_id))[1],
                                            'question': condition.line.question,
                                        }
                                     )

        return old_choices

    def clean(self):
        cleaned_data = self.cleaned_data
        self.type_args = None

        if not self._errors and self.initial_choices:
            choices_2_del = list(self.instance.poll_line_type.get_deleted_choices()) #TODO cache poll_line_type (in line ?)
            choices_2_del.extend(self.choices_2_del)

            choices_2_keep = self.choices_2_keep
            choices_2_keep.extend(enumerate(filter(None, #TODO: factorise ---> in a new field 'MultipleCharField'
                                            (choice.strip() for choice in cleaned_data.get('new_choices', '').split('\n'))
                                           ),
                                     start=len(choices_2_keep) + len(choices_2_del) + 1,
                                    )
                          )

            self.type_args = PollLineType.build_serialized_args(ptype=self.instance.type,
                                                                choices=choices_2_keep,
                                                                del_choices=choices_2_del,
                                                               ) #can raise Validation errors

        return cleaned_data

    def save(self, *args, **kwargs):
        if self.type_args:
            self.instance.type_args = self.type_args

        return super(PollFormLineEditForm, self).save(*args, **kwargs)


class PollFormLineConditionsForm(CremeForm):
    use_or     = TypedChoiceField(label=_(u'Use OR or AND between conditions'),
                                  choices=[(0, _('AND')), (1, _('OR'))],
                                  coerce=lambda x: bool(int(x))
                                 )
    conditions = PollFormLineConditionsField(label=_('Conditions'), required=False)

    def __init__(self, entity, *args, **kwargs):
        super(PollFormLineConditionsForm, self).__init__(*args, **kwargs)
        self.line = line = self.initial['line']
        self.old_conditions = conditions = line.get_conditions()

        fields = self.fields
        #fields['use_or'].initial = int(line.conds_use_or)
        fields['use_or'].initial = int(bool(line.conds_use_or)) #TODO: remove 'bool' if no more nullable

        conditions_f = fields['conditions']
        conditions_f.sources = entity.lines.filter(order__lt=line.order)
        conditions_f.initial = conditions

    def save(self, *args, **kwargs):
        line  = self.line
        cdata = self.cleaned_data

        update_model_instance(line, conds_use_or=cdata['use_or'])

        conds2del = []

        #TODO: select for update ??
        for old_condition, condition in map(None, self.old_conditions, cdata['conditions']):
            if not condition: #less new conditions that old conditions => delete conditions in excess
                conds2del.append(old_condition.id)
            elif not old_condition:
                condition.line = line
                condition.save()
            elif old_condition.update(condition):
                old_condition.save()

        if conds2del:
            PollFormLineCondition.objects.filter(pk__in=conds2del).delete()
