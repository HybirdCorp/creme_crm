# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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
from typing import Type, TYPE_CHECKING

# from django.db.models import ForeignKey
from django.forms import Field, ValidationError  # ChoiceField
from django.utils.translation import gettext_lazy as _  # pgettext_lazy

from creme.creme_core.forms.base import CremeModelForm  # CremeForm
from creme.creme_core.forms.widgets import DynamicSelect
from creme.creme_core.models import InstanceBrickConfigItem  # CremeEntity RelationType
# from creme.creme_core.utils.meta import ModelFieldEnumerator
from creme.creme_core.utils.unicode_collation import collator

from .. import get_rgraph_model
from ..bricks import ReportGraphBrick
from ..core.graph.fetcher import GraphFetcher

if TYPE_CHECKING:
    from ..models import AbstractReportGraph

# InstanceBrickConfigItemError = get_rgraph_model().InstanceBrickConfigItemError


class FetcherChoiceIterator:
    def __init__(self, graph: 'AbstractReportGraph', separator='|'):
        self.graph = graph
        self.separator = separator

    def build_fetcher_choices(self, fetcher_cls: Type[GraphFetcher], model):
        type_id = fetcher_cls.type_id
        sep = self.separator

        for value, label in fetcher_cls.choices(model):
            yield f'{type_id}{sep}{value}', label

    def __iter__(self):
        graph = self.graph

        if not graph:
            return

        registry = graph.fetcher_registry
        model    = graph.model
        sort_key = collator.sort_key
        build_choices = partial(self.build_fetcher_choices, model=model)

        # No group ----
        choices = []
        for fetcher_cls in registry.fetcher_classes:
            if not fetcher_cls.choices_group_name:
                choices.extend(build_choices(fetcher_cls=fetcher_cls))

        choices.sort(key=lambda c: sort_key(c[1]))
        yield from choices

        # Grouped choices ---
        fetcher_classes_by_group = []
        for fetcher_cls in registry.fetcher_classes:
            group_name = str(fetcher_cls.choices_group_name)
            if group_name:
                fetcher_classes_by_group.append((group_name, fetcher_cls))
        fetcher_classes_by_group.sort(key=lambda c: sort_key(c[0]))

        for group_name, fetcher_cls in fetcher_classes_by_group:
            choices = [*build_choices(fetcher_cls=fetcher_cls)]
            if choices:
                choices.sort(key=lambda c: sort_key(c[1]))

                yield group_name, choices


class GraphFetcherField(Field):
    widget = DynamicSelect(attrs={'autocomplete': True})
    default_error_messages = {
        'invalid_choice': _('Select a valid choice. %(value)s is not one of the available choices.'),
    }

    _graph: 'AbstractReportGraph'
    choice_iterator_class = FetcherChoiceIterator
    _choice_separator: str # Separate the type & the value of each fetcher choice

    def __init__(self, *, graph=None, choice_separator='|', **kwargs):
        super().__init__(**kwargs)
        self._choice_separator = choice_separator
        self.graph = graph

    def _update_choices(self):
        self.widget.choices = self.choice_iterator_class(
            graph=self._graph,
            separator=self._choice_separator,
        )

    @property
    def choice_separator(self):
        return self._choice_separator

    @choice_separator.setter
    def choice_separator(self, sep):
        self._choice_separator = sep
        self._update_choices()

    @property
    def graph(self):
        return self._graph

    @graph.setter
    def graph(self, graph):
        self._graph = graph
        self._update_choices()

    def to_python(self, value):
        """Returns a GraphFetcher."""
        if not value:
            return None

        fetcher_type_id, __, fetcher_value = value.partition(self._choice_separator)
        graph = self.graph
        fetcher = graph.fetcher_registry.get(
            graph=graph,
            fetcher_dict={
                GraphFetcher.DICT_KEY_TYPE:  fetcher_type_id,
                GraphFetcher.DICT_KEY_VALUE: fetcher_value,
            },
        )

        if fetcher.error:
            raise ValidationError(
                self.error_messages['invalid_choice'],
                code='invalid_choice',
                params={'value': value},
            )

        return fetcher


# class GraphInstanceBrickForm(CremeForm):
class GraphInstanceBrickForm(CremeModelForm):
    # volatile_column = ChoiceField(label=_('Volatile column'), choices=(), required=False,
    #                               widget=DynamicSelect(attrs={'autocomplete': True}),
    #                               help_text=_('When the graph is displayed on the detail-view of an entity, '
    #                                           'only the entities linked to this entity by the following link '
    #                                           'are used to compute the graph.'
    #                                          ),
    #                              )
    fetcher = GraphFetcherField(
        label=_('Volatile column'),
        help_text=_(
            'When the graph is displayed on the detail-view of an entity, '
            'only the entities linked to this entity by the following link '
            'are used to compute the graph.'
        ),
    )

    error_messages = {
        'duplicated': _('The instance block for «{graph}» with these parameters already exists!'),
    }

    class Meta(CremeModelForm.Meta):
        model = InstanceBrickConfigItem

    brick_class = ReportGraphBrick

    # def __init__(self, graph, instance=None, *args, **kwargs):
    def __init__(self, graph, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.graph = graph
        # self.fields['volatile_column'].choices = self._get_volatile_choices(graph.linked_report.ct)
        self.fields['fetcher'].graph = graph

    # def _get_volatile_choices(self, ct):
    #     choices = []
    #     fk_choices = [('fk-' + name, vname)
    #                     for name, vname in ModelFieldEnumerator(ct.model_class(), deep=0, only_leafs=False)
    #                                         .filter((lambda f, deep: isinstance(f, ForeignKey) and
    #                                                                  issubclass(f.remote_field.model, CremeEntity)
    #                                                 ),
    #                                                 viewable=True,
    #                                                )
    #                                         .choices()
    #                  ]
    #
    #     self._rtypes = {}
    #     rtype_choices = []
    #
    #     for rtype in RelationType.objects.compatible(ct, include_internals=True):
    #         rtype_choices.append(('rtype-' + rtype.id, str(rtype)))
    #         self._rtypes[rtype.id] = rtype
    #
    #     if fk_choices:
    #         choices.append((_('Fields'), fk_choices))
    #
    #     if rtype_choices:
    #         choices.append((_('Relationships'), rtype_choices))
    #
    #     if not choices:
    #         choices.append(('', _('No available choice')))
    #     else:
    #         choices.insert(0, ('', pgettext_lazy('reports-volatile_choice', 'None')))
    #
    #     return choices

    # def clean(self):
    #     cleaned_data = super().clean()
    #     volatile_column = cleaned_data.get('volatile_column')
    #     kwargs = {}
    #
    #     if volatile_column:
    #         link_type, link_val = volatile_column.split('-', 1)
    #
    #         if link_type == 'fk':
    #             kwargs['volatile_field'] = link_val
    #         else:
    #             kwargs['volatile_rtype'] = self._rtypes[link_val]
    #
    #     try:
    #         self.ibci = self.graph.create_instance_brick_config_item(save=False, **kwargs)
    #     except InstanceBrickConfigItemError as e:
    #         raise ValidationError(str(e)) from e
    #
    #     return cleaned_data

    def clean_fetcher(self):
        fetcher: 'GraphFetcher' = self.cleaned_data['fetcher']
        graph = self.graph
        extra_items = dict(fetcher.as_dict_items())

        for ibci in InstanceBrickConfigItem.objects.filter(
            entity=graph.id,
            brick_class_id=self.brick_class.id_,
        ):
            if extra_items == dict(ibci.extra_data_items):
                raise ValidationError(
                    self.error_messages['duplicated'].format(graph=graph),
                    code='duplicated',
                )

        return fetcher

    # def save(self):
    #     ibci = self.ibci
    #     ibci.save()
    #
    #     return ibci
    def save(self, *args, **kwargs):
        ibci: InstanceBrickConfigItem = self.instance
        ibci.brick_class_id = self.brick_class.id_
        ibci.entity = self.graph

        for k, v in self.cleaned_data['fetcher'].as_dict_items():
            ibci.set_extra_data(key=k, value=v)

        return super().save(*args, **kwargs)
