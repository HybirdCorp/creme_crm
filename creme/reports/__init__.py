################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2025  Hybird
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

from django.conf import settings

from creme.creme_core import get_concrete_model


def report_model_is_custom():
    return (
        settings.REPORTS_REPORT_MODEL != 'reports.Report'
        and not settings.REPORTS_REPORT_FORCE_NOT_CUSTOM
    )


# def rgraph_model_is_custom():
#     return (
#         settings.REPORTS_GRAPH_MODEL != 'reports.ReportGraph'
#         and not settings.REPORTS_GRAPH_FORCE_NOT_CUSTOM
#     )


def get_report_model():
    "Returns the Report model that is active in this project."
    return get_concrete_model('REPORTS_REPORT_MODEL')


# def get_rgraph_model():
#     "Returns the ReportGraph model that is active in this project."
#     return get_concrete_model('REPORTS_GRAPH_MODEL')
