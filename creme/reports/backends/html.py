# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from django.template.loader import render_to_string

from .base import ReportBackend

LIMIT_TO = 25


class HtmlReportBackend(ReportBackend):
    def __init__(self, report, context_instance, template="reports/backends/html_report.html", limit_to=None, extra_fetch_q=None ):
        super(HtmlReportBackend, self).__init__(report)
        self.context_instance = context_instance
        self.template = template
        self.limit_to = limit_to
        self.extra_fetch_q = extra_fetch_q

    def render(self):
        user = self.context_instance['user']
#        return render_to_string(self.template, {'backend': self, 'lines':self.report.fetch_all_lines(limit_to=self.limit_to)}, context_instance=self.context_instance)
        return render_to_string(self.template, {'backend': self, 'lines':self.report.fetch_all_lines(limit_to=self.limit_to, extra_q=self.extra_fetch_q, user=user)}, context_instance=self.context_instance)

