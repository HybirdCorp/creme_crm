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
from creme_core.forms import CremeForm, CremeModelForm
from creme_core.forms.fields import MultiGenericEntityField
from creme_core.forms.widgets import UnorderedMultipleChoiceWidget

from graphs.models import RootNode


class AddRootNodesForm(CremeForm):
    entities       = MultiGenericEntityField(label=_(u'Root entities'))
    relation_types = ModelMultipleChoiceField(label=_('Related types of relations'),
                                              queryset=RelationType.objects.all(),
                                              widget=UnorderedMultipleChoiceWidget)

    def __init__(self, entity, *args, **kwargs):
        super(AddRootNodesForm, self).__init__(*args, **kwargs)
        self.graph = entity
        entities_field = self.fields['entities']
        entities_field.initial = [[(entities_field.get_ctypes()[0].pk, None)]]

    def save(self):
        graph = self.graph
        cleaned_data = self.cleaned_data
        entities = cleaned_data['entities']
        rtypes = cleaned_data['relation_types']
        create_node = RootNode.objects.create

        for entity in entities:
            root_node = create_node(entity=entity, graph=graph)
            root_node.relation_types = rtypes


class EditRootNodeForm(CremeModelForm):
    relation_types = ModelMultipleChoiceField(label=_('Related types of relations'),
                                              queryset=RelationType.objects.all(),
                                              widget=UnorderedMultipleChoiceWidget)

    class Meta:
        model = RootNode
        exclude = ('graph', 'entity')

    def __init__(self, entity, *args, **kwargs): #NB only useful for the generic view edit_related_to_entity()
        super(EditRootNodeForm, self).__init__(*args, **kwargs)
        self.graph = entity
