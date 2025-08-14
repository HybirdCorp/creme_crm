################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2024  Hybird
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

from django import template

register = template.Library()


# TODO: "report_charts" argument instead of 'takes_context'?
@register.inclusion_tag(
    'reports/templatetags/report_chart_selectors.html',
    takes_context=True,
)
def reports_chart_selector(context, rgraph):
    context['rgraph'] = rgraph
    return context


@register.filter
def reports_chart_labels(charts):
    return {name: chart.label for name, chart in charts}
