# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2020  Hybird
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

# from typing import Optional, TYPE_CHECKING
#
# from django.db.models import FieldDoesNotExist, QuerySet
# from django.utils.translation import gettext_lazy as _
#
# from creme.creme_core.models import CustomField
#
# from creme.reports.report_aggregation_registry import field_aggregation_registry
#
# if TYPE_CHECKING:
#     from creme.reports.models import AbstractReportGraph
#
#
# class ReportGraphYCalculator:
#     def __init__(self):
#         self.error: Optional[str] = None
#
#     def __call__(self, entities: QuerySet):
#         return 0
#
#     @staticmethod
#     def build(graph: 'AbstractReportGraph') -> 'ReportGraphYCalculator':
#         calculator: 'ReportGraphYCalculator'
#
#         if graph.is_count:
#             calculator = RGYCCount()
#         else:
#             ordinate = graph.ordinate
#             ordinate_col, sep, aggregation_name = ordinate.rpartition('__')
#             aggregation = field_aggregation_registry.get(aggregation_name)
#
#             if ordinate_col.isdigit():  # CustomField
#                 try:
#                     calculator = RGYCCustomField(CustomField.objects.get(
#                     pk=ordinate_col), aggregation)
#                 except CustomField.DoesNotExist:
#                     calculator = ReportGraphYCalculator()
#                     calculator.error = _('the custom field does not exist any more.')
#             else:  # Regular Field
#                 try:
#                     field = graph.model._meta.get_field(ordinate_col)
#                 except FieldDoesNotExist:
#                     calculator = ReportGraphYCalculator()
#                     calculator.error = _('the field does not exist any more.')
#                 else:
#                     calculator = RGYCField(field, aggregation)
#
#         return calculator
#
#     @property
#     def verbose_name(self) -> str:
#         return '??'
#
#
# class RGYCCount(ReportGraphYCalculator):
#     def __call__(self, entities):
#         return entities.count()
#
#     @property
#     def verbose_name(self):
#         return _('Count')
#
#
# class RGYCAggregation(ReportGraphYCalculator):
#     def __init__(self, aggregation, aggregate_value):
#         super().__init__()
#         self._aggregation = aggregation
#         self._aggregate_value = aggregate_value
#
#     def __call__(self, entities):
#         return entities.aggregate(
#             rgyc_value_agg=self._aggregate_value,
#         ).get('rgyc_value_agg') or 0
#
#     def _name(self):
#         raise NotImplementedError
#
#     @property
#     def verbose_name(self):
#         return f'{self._name()} - {self._aggregation.title}'
#
#
# class RGYCField(RGYCAggregation):
#     def __init__(self, field, aggregation):
#         super().__init__(aggregation, aggregation.func(field.name))
#         self._field = field
#
#     def _name(self):
#         return self._field.verbose_name
#
#
# class RGYCCustomField(RGYCAggregation):
#     def __init__(self, cfield, aggregation):
#         super().__init__(
#             aggregation,
#             aggregation.func(f'{cfield.get_value_class().get_related_name()}__value'),
#         )
#         self._cfield = cfield
#
#     def _name(self):
#         return self._cfield.name
