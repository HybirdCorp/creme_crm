################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms import CremeForm
from creme.creme_core.forms.widgets import UnorderedMultipleChoiceWidget
from creme.creme_core.models import RelationType


class AddRelationTypesForm(CremeForm):
    relation_types = ModelMultipleChoiceField(
        label=_('Types of the peripheral relations'),
        queryset=RelationType.objects.none(),
        widget=UnorderedMultipleChoiceWidget(columntype='wide'),
    )

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.graph = entity
        self.fields['relation_types'].queryset = RelationType.objects.exclude(
            pk__in=entity.orbital_relation_types.all(),
        ).filter(enabled=True)

    def save(self):
        add_rtype = self.graph.orbital_relation_types.add
        for rtype in self.cleaned_data['relation_types']:
            add_rtype(rtype)
