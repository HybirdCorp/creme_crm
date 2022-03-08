# -*- coding: utf-8 -*-

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

from functools import partial

from django.forms import ModelMultipleChoiceField
from django.utils.encoding import smart_str
from django.utils.translation import gettext_lazy as _

import creme.creme_core.forms as core_forms
from creme.creme_core.forms.fields import MultiGenericEntityField
from creme.creme_core.models import RelationType

from ..models import RootNode


class RelationTypeMultipleChoiceField(ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return smart_str(obj.predicate)


class AddRootNodesForm(core_forms.CremeForm):
    entities = MultiGenericEntityField(label=_('Root entities'))
    relation_types = RelationTypeMultipleChoiceField(
        label=_('Related types of relations'), queryset=RelationType.objects.all(),
    )

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.graph = entity
        entities_field = self.fields['entities']
        entities_field.initial = [[(entities_field.get_ctypes()[0].pk, None)]]

    def save(self):
        cleaned_data = self.cleaned_data
        rtypes = cleaned_data['relation_types']
        create_node = partial(RootNode.objects.create, graph=self.graph)

        for entity in cleaned_data['entities']:
            # root_node = create_node(entity=entity)
            root_node = create_node(real_entity=entity)
            root_node.relation_types.set(rtypes)


class EditRootNodeForm(core_forms.CremeModelForm):
    relation_types = RelationTypeMultipleChoiceField(
        label=_('Related types of relations'), queryset=RelationType.objects.all(),
    )

    class Meta:
        model = RootNode
        exclude = ()

    # NB only useful for the generic view edit_related_to_entity()
    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.graph = entity
