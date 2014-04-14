# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2014  Hybird
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

from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponse
from django.template.defaultfilters import slugify

from .base import ExportBackend


class CSVExportBackend(ExportBackend):
    id = 'csv'
    verbose_name = _(u"CSV File (delimiter: ',')")
    delimiter = ','
    help_text = ''

    def __init__(self):
        self.response = HttpResponse(mimetype='text/csv')
        self.writer = csv.writer(self.response, quoting=csv.QUOTE_ALL, delimiter=self.delimiter)

    def writerow(self, row):
        return self.writer.writerow(row)

    def save(self, filename):
        self.response['Content-Disposition'] = 'attachment; filename="%s.csv"' % slugify(filename)


class SemiCSVExportBackend(CSVExportBackend):
    id = 'scsv'
    verbose_name = _(u"CSV File (delimiter: ';')")
    delimiter = ';'
    help_text = ''
