# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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
from django.forms import ModelMultipleChoiceField
from django.utils.translation import gettext_lazy as _

# from .. import get_graph_model
from creme.creme_core.forms import CremeForm  # CremeEntityForm
from creme.creme_core.forms.widgets import UnorderedMultipleChoiceWidget
from creme.creme_core.models import RelationType

# class GraphForm(CremeEntityForm):
#     class Meta(CremeEntityForm.Meta):
#         model = get_graph_model()
#
#     def __init__(self, *args, **kwargs):
#         warnings.warn('GraphForm is deprecated.', DeprecationWarning)
#         super().__init__(*args, **kwargs)


class AddRelationTypesForm(CremeForm):
    relation_types = ModelMultipleChoiceField(
        label=_('Types of the peripheral relations'),
        queryset=RelationType.objects.all(),
        widget=UnorderedMultipleChoiceWidget(columntype='wide'),
    )

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.graph = entity
        self.fields['relation_types'].queryset = RelationType.objects.exclude(
            pk__in=entity.orbital_relation_types.all(),
        )

    def save(self):
        add_rtype = self.graph.orbital_relation_types.add
        for rtype in self.cleaned_data['relation_types']:
            add_rtype(rtype)
