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

import csv

from django.http import HttpResponse
from django.utils.encoding import smart_str

from base import ReportBackend


class CsvReportBackend(ReportBackend):
    def __init__(self, report):
        super(CsvReportBackend, self).__init__(report)

    def render_to_response(self):
        report = self.report

        response = HttpResponse(mimetype='text/csv')
        response['Content-Disposition'] = 'attachment; filename="%s.csv"' % smart_str(report.name)

        writer   = csv.writer(response, delimiter=";")

        writerow = writer.writerow

        writerow([smart_str(column.title) for column in report.get_children_fields_flat()])

        for line in report.fetch_all_lines():
            writerow([smart_str(value) for value in line])

        return response



