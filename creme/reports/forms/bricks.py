# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from django.db.models import ForeignKey
from django.forms import ChoiceField, ValidationError
from django.utils.translation import ugettext_lazy as _, pgettext_lazy

from creme.creme_core.forms.base import CremeForm
from creme.creme_core.forms.widgets import DynamicSelect
from creme.creme_core.models import CremeEntity, RelationType
from creme.creme_core.utils.meta import ModelFieldEnumerator

from .. import get_rgraph_model


# InstanceBlockConfigItemError = get_rgraph_model().InstanceBlockConfigItemError
InstanceBrickConfigItemError = get_rgraph_model().InstanceBrickConfigItemError


class GraphInstanceBrickForm(CremeForm):
    volatile_column = ChoiceField(label=_(u'Volatile column'), choices=(), required=False,
                                  widget=DynamicSelect(attrs={'autocomplete': True}),
                                  help_text=_(u'When the graph is displayed on the detailview of an entity, '
                                              u'only the entities linked to this entity by the following link '
                                              u'are used to compute the graph.'
                                             ),
                                 )

    def __init__(self, graph, *args, **kwargs):
        # super(GraphInstanceBrickForm, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)
        self.graph = graph
        # self.fields['volatile_column'].choices = self._get_volatile_choices(graph.report.ct)
        self.fields['volatile_column'].choices = self._get_volatile_choices(graph.linked_report.ct)

    def _get_volatile_choices(self, ct):
        choices = []
        fk_choices = [('fk-' + name, vname)
                        for name, vname in ModelFieldEnumerator(ct.model_class(), deep=0, only_leafs=False)
                                            .filter((lambda f, deep: isinstance(f, ForeignKey) and
                                                                     # issubclass(f.rel.to, CremeEntity)
                                                                     issubclass(f.remote_field.model, CremeEntity)
                                                    ),
                                                    viewable=True,
                                                   )
                                            .choices()
                     ]

        self._rtypes = {}
        rtype_choices = []

        for rtype in RelationType.get_compatible_ones(ct, include_internals=True):
            rtype_choices.append(('rtype-' + rtype.id, str(rtype)))
            self._rtypes[rtype.id] = rtype

        if fk_choices:
            choices.append((_(u'Fields'), fk_choices))

        if rtype_choices:
            choices.append((_(u'Relationships'), rtype_choices))

        if not choices:
            choices.append(('', _(u'No available choice')))
        else:
            choices.insert(0, ('', pgettext_lazy('reports-volatile_choice', u'None')))

        return choices

    def clean(self):
        # cleaned_data = super(GraphInstanceBrickForm, self).clean()
        cleaned_data = super().clean()
        volatile_column = cleaned_data.get('volatile_column')
        kwargs = {}

        if volatile_column:
            link_type, link_val = volatile_column.split('-', 1)

            if link_type == 'fk':
                kwargs['volatile_field'] = link_val
            else:
                kwargs['volatile_rtype'] = self._rtypes[link_val]

        try:
            # self.ibci = self.graph.create_instance_block_config_item(save=False, **kwargs)
            self.ibci = self.graph.create_instance_brick_config_item(save=False, **kwargs)
        # except InstanceBlockConfigItemError as e:
        except InstanceBrickConfigItemError as e:
            raise ValidationError(str(e)) from e

        return cleaned_data

    def save(self):
        ibci = self.ibci
        ibci.save()

        return ibci
