################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024-2025  Hybird
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

from creme.creme_core.core.cloning import EntityCloner
from creme.creme_core.core.copying import PostSaveCopier, RegularFieldsCopier


class ReportFieldsCopier(PostSaveCopier):
    def copy_to(self, target):
        for rfield in self._source.fields.all():
            rfield.clone(report=target)


# class ReportGraphesCopier(PostSaveCopier):
#     def copy_to(self, target):
#         source = self._source
#
#         for graph in source.reportgraph_set.all():
#             new_graph = type(graph)()
#             RegularFieldsCopier(user=self._user, source=graph).copy_to(target=new_graph)
#             new_graph.linked_report = target
#
#             new_graph.save()
class ReportChartsCopier(PostSaveCopier):
    def copy_to(self, target):
        source = self._source

        for chart in source.charts.all():
            new_chart = type(chart)()
            user = self._user

            RegularFieldsCopier(user=user, source=chart).copy_to(target=new_chart)
            new_chart.linked_report = target
            new_chart.user = user

            new_chart.save()


class ReportCloner(EntityCloner):
    post_save_copiers = [
        *EntityCloner.post_save_copiers,
        ReportFieldsCopier,
        # ReportGraphesCopier,
        ReportChartsCopier,
    ]
