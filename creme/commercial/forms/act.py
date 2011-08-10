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

from math import ceil

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _, ugettext
from django.forms import ModelChoiceField, IntegerField

from creme_core.forms import CremeForm, CremeEntityForm, CremeModelForm, CremeDateTimeField
from creme_core.utils import Q_creme_entity_content_types

from commercial.models import Act, ActObjective, ActObjectivePattern, ActObjectivePatternComponent


class ActForm(CremeEntityForm):
    start    = CremeDateTimeField(label=_(u"Start"))
    due_date = CremeDateTimeField(label=_(u"Due date"))

    class Meta(CremeEntityForm.Meta):
        model = Act

    def clean(self):
        cleaned_data = self.cleaned_data

        if not self._errors:
            if cleaned_data['due_date'] < cleaned_data['start']:
                raise ValidationError(_(u"Due date can't be before start."))

        return cleaned_data

class ObjectiveForm(CremeModelForm):
    class Meta:
        model = ActObjective
        fields = ('name', 'counter_goal', 'ctype')

    def __init__(self, entity, *args, **kwargs):
        super(ObjectiveForm, self).__init__(*args, **kwargs)
        self.act = entity
        fields = self.fields

        fields['counter_goal'].help_text = ugettext(u'Integer value the counter has to reach')

        ctype_field = fields['ctype']
        ctype_field.queryset = Q_creme_entity_content_types()
        ctype_field.empty_label = ugettext(u'Do not count entity')

    def save(self, *args, **kwargs):
        self.instance.act = self.act
        super(ObjectiveForm, self).save(*args, **kwargs)


class ObjectivesFromPatternForm(CremeForm):
    pattern = ModelChoiceField(label=_(u'Pattern'), empty_label=None,
                               queryset=ActObjectivePattern.objects.all()
                              )

    def __init__(self, entity, *args, **kwargs):
        super(ObjectivesFromPatternForm, self).__init__(*args, **kwargs)
        self.act = entity

        self.fields['pattern'].queryset = ActObjectivePattern.objects.filter(segment=entity.segment_id)

    def save(self, *args, **kwargs):
        act = self.act
        pattern = self.cleaned_data['pattern']
        create_objective = ActObjective.objects.create
        won_opps = int(ceil(float(act.expected_sales) / float(pattern.average_sales)))

        create_objective(act=act, name=ugettext(u'Number of won opportunities'), counter_goal=won_opps)

        def create_objectives_from_components(comps, parent_goal):
            for comp in comps:
                counter_goal = int(ceil(parent_goal * (100.0 / comp.success_rate)))
                create_objective(act=act, name=comp.name, ctype_id=comp.ctype_id, counter_goal=counter_goal)
                create_objectives_from_components(comp.get_children(), counter_goal)

        create_objectives_from_components(pattern.get_components_tree(), won_opps)


class ObjectivePatternForm(CremeEntityForm):
    class Meta(CremeEntityForm.Meta):
        model = ActObjectivePattern


class _PatternComponentForm(CremeModelForm):
    success_rate = IntegerField(label=_(u'Success rate'), min_value=1, max_value=100,
                                help_text=_(u'Percentage of success')
                               )

    class Meta:
        model = ActObjectivePatternComponent
        exclude = ('pattern', 'parent')

    def __init__(self, *args, **kwargs):
        super(_PatternComponentForm, self).__init__(*args, **kwargs)

        #TODO: factorise with ObjectiveForm ??
        ctype_field = self.fields['ctype']
        ctype_field.queryset = Q_creme_entity_content_types()
        ctype_field.empty_label = ugettext(u'Do not count entity')


class PatternComponentForm(_PatternComponentForm):
    def __init__(self, entity, *args, **kwargs):
        super(PatternComponentForm, self).__init__(*args, **kwargs)
        self.pattern = entity

    def save(self, *args, **kwargs):
        self.instance.pattern = self.pattern
        return super(PatternComponentForm, self).save(*args, **kwargs)


class PatternChildComponentForm(_PatternComponentForm):
    def __init__(self, parent, *args, **kwargs):
        super(PatternChildComponentForm, self).__init__(*args, **kwargs)
        self.parent = parent

    def save(self, *args, **kwargs):
        parent = self.parent
        instance = self.instance

        instance.pattern = parent.pattern
        instance.parent = parent
        return super(PatternChildComponentForm, self).save(*args, **kwargs)


class PatternParentComponentForm(_PatternComponentForm):
    def __init__(self, child, *args, **kwargs):
        super(PatternParentComponentForm, self).__init__(*args, **kwargs)
        self.child = child

    def save(self, *args, **kwargs):
        child = self.child
        instance = self.instance

        instance.pattern = child.pattern
        instance.parent = child.parent
        super(PatternParentComponentForm, self).save(*args, **kwargs)

        child.parent = instance
        child.save() #TODO: use *args/**kwargs ('using' arg)???

        return instance
