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

from django.forms import ModelMultipleChoiceField
from django.utils.translation import ugettext_lazy as _

from creme_core.models import RelationType
from creme_core.forms import CremeForm, CremeEntityForm
from creme_core.forms.widgets import UnorderedMultipleChoiceWidget

from graphs.models import Graph


class GraphForm(CremeEntityForm):
    class Meta(CremeEntityForm.Meta):
        model = Graph
        exclude = CremeEntityForm.Meta.exclude + ('orbital_relation_types', )


class AddRelationTypesForm(CremeForm):
    relation_types = ModelMultipleChoiceField(label=_('Types of the peripheral relations'),
                                              queryset=RelationType.objects.all(),
                                              widget=UnorderedMultipleChoiceWidget)

    def __init__(self, entity, *args, **kwargs):
        super(AddRelationTypesForm, self).__init__(*args, **kwargs)
        self.graph = entity

        self.fields['relation_types'].queryset = RelationType.objects.exclude(pk__in=entity.orbital_relation_types.all())

    def save(self):
        relation_types = self.graph.orbital_relation_types
        for rtype in self.cleaned_data['relation_types']:
            relation_types.add(rtype)

