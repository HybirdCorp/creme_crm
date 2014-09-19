# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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
from django.forms import ChoiceField, ValidationError #CharField
from django.utils.translation import ugettext_lazy as _, pgettext_lazy

from creme.creme_core.forms.base import CremeForm
from creme.creme_core.forms.widgets import DynamicSelect
from creme.creme_core.models import CremeEntity, RelationType
from creme.creme_core.utils.meta import ModelFieldEnumerator

from ..models import ReportGraph


class GraphInstanceBlockForm(CremeForm):
    #graph           = CharField(label=_(u"Related graph"), widget=Label(), required=False)
    volatile_column = ChoiceField(label=_(u'Volatile column'), choices=(), required=False,
                                  widget=DynamicSelect(attrs={'autocomplete': True}),
                                  help_text=_("When the graph is displayed on the detailview of an entity, "
                                              "only the entities linked to this entity by the following link "
                                              "are used to compute the graph."
                                             )
                                 )

    def __init__(self, graph, *args, **kwargs):
        super(GraphInstanceBlockForm, self).__init__(*args, **kwargs)
        self.graph = graph
        report = graph.report
        fields = self.fields
        fields['volatile_column'].choices = self._get_volatile_choices(report.ct)
        #fields['graph'].initial = u"%s - %s" % (graph, report)

    def _get_volatile_choices(self, ct):
        choices = []
        fk_choices = [('fk-' + name, vname)
                        for name, vname in ModelFieldEnumerator(ct.model_class(), deep=0, only_leafs=False)
                                            .filter((lambda f, deep: isinstance(f, ForeignKey) and
                                                                     issubclass(f.rel.to, CremeEntity)
                                                    ),
                                                    viewable=True,
                                                   )
                                            .choices()
                     ]

        self._rtypes = {}
        rtype_choices = []

        for rtype in RelationType.get_compatible_ones(ct, include_internals=True):
            rtype_choices.append(('rtype-' + rtype.id, unicode(rtype)))
            self._rtypes[rtype.id] = rtype

        if fk_choices:
            choices.append((_('Fields'), fk_choices))

        if rtype_choices:
            choices.append((_('Relationships'), rtype_choices))

        if not choices:
            choices.append(('', _('No available choice')))
        else:
            choices.insert(0, ('', pgettext_lazy('reports-volatile_choice', 'None')))

        return choices

    def clean(self):
        cleaned_data = super(GraphInstanceBlockForm, self).clean()
        volatile_column = cleaned_data.get('volatile_column')
        kwargs = {}

        if volatile_column:
           link_type, link_val = volatile_column.split('-', 1)

           if link_type == 'fk':
                kwargs['volatile_field'] = link_val
           else:
                kwargs['volatile_rtype'] = self._rtypes[link_val]

        try:
            self.ibci = self.graph.create_instance_block_config_item(save=False, **kwargs)
        except ReportGraph.InstanceBlockConfigItemError as e:
            raise ValidationError(unicode(e))

        return cleaned_data

    def save(self):
        ibci = self.ibci
        ibci.save()

        return ibci
