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

from django.forms.util import ValidationError
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.forms.fields import JSONField
from creme.creme_core.forms.widgets import SelectorList, ChainedInput

from ..models import PollFormLineCondition


class PollFormLineConditionsWidget(SelectorList):
    def __init__(self, sources, attrs=None):
        chained_input = ChainedInput(attrs)
        attrs = {'auto': False}
        add = chained_input.add_dselect
        add('source', attrs=attrs, options=[(src.id, src.question) for src in sources])
        add('choice', attrs=attrs, options='/polls/pform_line/${source}/choices')

        super(PollFormLineConditionsWidget, self).__init__(chained_input)


class PollFormLineConditionsField(JSONField):
    default_error_messages = {
        'invalidsource': _('This source is invalid.'),
        'invalidchoice': _('This choice is invalid.'),
    }
    value_type = list

    def __init__(self, sources=(), *args, **kwargs):
        super(PollFormLineConditionsField, self).__init__(*args, **kwargs)
        self.sources = sources

    @property
    def sources(self):
        return self._sources

    @sources.setter
    def sources(self, sources):
        "@param sources Sequence of PollFormLines"
        self._sources = [source for source in sources if source.poll_line_type.get_choices()]

        self._build_widget()

    def _create_widget(self):
        return PollFormLineConditionsWidget(self._sources)

    def _value_to_jsonifiable(self, value):
        return [{'source': condition.source_id, 'choice': condition.raw_answer}
                    for condition in value
               ]

    def _clean_source(self, entry):
        line_id = self.clean_value(entry, 'source', int)

        for line in self.sources:
            if line_id == line.id:
                return line

        raise ValidationError(self.error_messages['invalidsource'])

    def _clean_choice(self, entry, source):
        choice = self.clean_value(entry, 'choice', int)
        items  = source.poll_line_type.get_choices()

        if not any(choice == item[0] for item in items):
            raise ValidationError(self.error_messages['invalidchoice'])

        return choice

    def _value_from_unjsonfied(self, data):
        clean_source = self._clean_source
        clean_choice = self._clean_choice
        conditions = []

        for entry in data:
            source = clean_source(entry)
            choice = clean_choice(entry, source)
            conditions.append(PollFormLineCondition(source=source,
                                                    operator=PollFormLineCondition.EQUALS,
                                                    raw_answer=source.poll_line_type.encode_condition(choice),
                                                   )
                             )

        return conditions
