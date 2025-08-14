################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from django.forms import Field, ValidationError
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms.base import CremeModelForm
from creme.creme_core.forms.widgets import DynamicSelect
from creme.creme_core.models import InstanceBrickConfigItem
from creme.creme_core.utils.unicode_collation import collator
# from creme.reports.bricks import ReportGraphChartInstanceBrick
from creme.reports.bricks import ReportChartInstanceBrick

# from ..core.graph.fetcher import GraphFetcher
from ..core.chart.fetcher import ChartFetcher

if TYPE_CHECKING:
    from ..models import ReportChart  # AbstractReportGraph


class FetcherChoiceIterator:
    # def __init__(self, graph: AbstractReportGraph, separator='|'):
    def __init__(self, chart: ReportChart, separator='|'):
        # self.graph = graph
        self.chart = chart
        self.separator = separator

    # def build_fetcher_choices(self, fetcher_cls: type[GraphFetcher], model):
    def build_fetcher_choices(self, fetcher_cls: type[ChartFetcher], model):
        type_id = fetcher_cls.type_id
        sep = self.separator

        for value, label in fetcher_cls.choices(model):
            yield f'{type_id}{sep}{value}', label

    def __iter__(self):
        # graph = self.graph
        chart = self.chart

        # if not graph:
        if not chart:
            return

        # registry = graph.fetcher_registry
        registry = chart.fetcher_registry
        # model    = graph.model
        model    = chart.model
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
        fetcher_classes_by_group = [
            (group_name, fetcher_cls)
            for fetcher_cls in registry.fetcher_classes
            if (group_name := str(fetcher_cls.choices_group_name))
        ]
        fetcher_classes_by_group.sort(key=lambda c: sort_key(c[0]))

        for group_name, fetcher_cls in fetcher_classes_by_group:
            choices = [*build_choices(fetcher_cls=fetcher_cls)]
            if choices:
                choices.sort(key=lambda c: sort_key(c[1]))

                yield group_name, choices


# class GraphFetcherField(Field):
class ChartFetcherField(Field):
    widget = DynamicSelect(attrs={'autocomplete': True})
    default_error_messages = {
        'invalid_choice': _(
            'Select a valid choice. %(value)s is not one of the available choices.'
        ),
    }

    # _graph: AbstractReportGraph
    _chart: ReportChart
    choice_iterator_class = FetcherChoiceIterator
    _choice_separator: str  # Separate the type & the value of each fetcher choice

    # def __init__(self, *, graph=None, choice_separator='|', **kwargs):
    #     super().__init__(**kwargs)
    #     self._choice_separator = choice_separator
    #     self.graph = graph
    def __init__(self, *, chart=None, choice_separator='|', **kwargs):
        super().__init__(**kwargs)
        self._choice_separator = choice_separator
        self.chart = chart

    def _update_choices(self):
        self.widget.choices = self.choice_iterator_class(
            # graph=self._graph,
            chart=self._chart,
            separator=self._choice_separator,
        )

    @property
    def choice_separator(self):
        return self._choice_separator

    @choice_separator.setter
    def choice_separator(self, sep):
        self._choice_separator = sep
        self._update_choices()

    # @property
    # def graph(self):
    #     return self._graph
    #
    # @graph.setter
    # def graph(self, graph):
    #     self._graph = graph
    #     self._update_choices()
    @property
    def chart(self) -> ReportChart:
        return self._chart

    @chart.setter
    def chart(self, value: ReportChart):
        self._chart = value
        self._update_choices()

    def to_python(self, value):
        """Returns a GraphFetcher."""
        if not value:
            return None

        fetcher_type_id, __, fetcher_value = value.partition(self._choice_separator)
        # graph = self.graph
        chart = self.chart
        # fetcher = graph.fetcher_registry.get(
        #     graph=graph,
        #     fetcher_dict={
        #         GraphFetcher.DICT_KEY_TYPE:  fetcher_type_id,
        #         GraphFetcher.DICT_KEY_VALUE: fetcher_value,
        #     },
        # )
        fetcher = chart.fetcher_registry.get(
            chart=chart,
            fetcher_dict={
                ChartFetcher.DICT_KEY_TYPE: fetcher_type_id,
                ChartFetcher.DICT_KEY_VALUE: fetcher_value,
            },
        )

        if fetcher.error:
            raise ValidationError(
                self.error_messages['invalid_choice'],
                code='invalid_choice',
                params={'value': value},
            )

        return fetcher


# class GraphInstanceBrickForm(CremeModelForm):
#     fetcher = GraphFetcherField(
#         label=_('Volatile column'),
#         help_text=_(
#             'When the chart is displayed on the detail-view of an entity, '
#             'only the entities linked to this entity by the following link '
#             'are used to compute the chart.\n'
#             'Notice: if you chose «No volatile column», the block will display '
#             'the same data on Home & on detail-views (it could be useful to get '
#             'a recall on general data anyway).',
#         ),
#     )
#
#     error_messages = {
#         'duplicated': _(
#             'The instance block for «{chart}» with these parameters already exists!'
#         ),
#     }
#
#     class Meta(CremeModelForm.Meta):
#         model = InstanceBrickConfigItem
#
#     brick_class = ReportGraphChartInstanceBrick
#
#     def __init__(self, graph, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.graph = graph
#         self.fields['fetcher'].graph = graph
#
#     def clean_fetcher(self) -> GraphFetcher:
#         fetcher: GraphFetcher = self.cleaned_data['fetcher']
#         graph = self.graph
#         extra_items = dict(fetcher.as_dict_items())
#
#         for ibci in InstanceBrickConfigItem.objects.filter(
#             entity=graph.id, brick_class_id=self.brick_class.id,
#         ):
#             if extra_items == dict(ibci.extra_data_items):
#                 raise ValidationError(
#                     self.error_messages['duplicated'].format(chart=graph),
#                     code='duplicated',
#                 )
#
#         return fetcher
#
#     def save(self, *args, **kwargs) -> InstanceBrickConfigItem:
#         ibci: InstanceBrickConfigItem = self.instance
#         ibci.brick_class_id = self.brick_class.id
#         ibci.entity = self.graph
#
#         for k, v in self.cleaned_data['fetcher'].as_dict_items():
#             ibci.set_extra_data(key=k, value=v)
#
#         return super().save(*args, **kwargs)
class ChartInstanceBrickForm(CremeModelForm):
    fetcher = ChartFetcherField(
        label=_('Volatile column'),
        help_text=_(
            'When the chart is displayed on the detail-view of an entity, '
            'only the entities linked to this entity by the following link '
            'are used to compute the chart.\n'
            'Notice: if you chose «No volatile column», the block will display '
            'the same data on Home & on detail-views (it could be useful to get '
            'a recall on general data anyway).',
        ),
    )

    error_messages = {
        'duplicated': _(
            'The instance block for «{chart}» with these parameters already exists!'
        ),
    }

    class Meta(CremeModelForm.Meta):
        model = InstanceBrickConfigItem

    brick_class = ReportChartInstanceBrick

    def __init__(self, chart, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chart = chart
        self.fields['fetcher'].chart = chart

    def clean_fetcher(self) -> ChartFetcher:
        fetcher: ChartFetcher = self.cleaned_data['fetcher']
        chart = self.chart
        extra_items = dict(fetcher.as_dict_items())
        extra_items[ReportChartInstanceBrick.chart_key] = str(self.chart.uuid)

        for ibci in InstanceBrickConfigItem.objects.filter(
            entity=chart.linked_report_id,
            brick_class_id=self.brick_class.id,
        ):
            if extra_items == dict(ibci.extra_data_items):
                raise ValidationError(
                    self.error_messages['duplicated'].format(chart=chart),
                    code='duplicated',
                )

        return fetcher

    def save(self, *args, **kwargs) -> InstanceBrickConfigItem:
        ibci: InstanceBrickConfigItem = self.instance
        ibci.brick_class_id = self.brick_class.id
        ibci.entity = self.chart.linked_report
        # TODO: factorise with ChartFetcher.create_brick_config_item()
        ibci.set_extra_data(
            key=ReportChartInstanceBrick.chart_key,
            value=str(self.chart.uuid),
        )

        for k, v in self.cleaned_data['fetcher'].as_dict_items():
            ibci.set_extra_data(key=k, value=v)

        return super().save(*args, **kwargs)
