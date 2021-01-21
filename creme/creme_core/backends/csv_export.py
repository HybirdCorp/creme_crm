# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2021  Hybird
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
from django.template.defaultfilters import slugify
from django.utils.translation import gettext_lazy as _

from .base import ExportBackend


class CSVExportBackend(ExportBackend):
    id = 'csv'
    verbose_name = _("CSV File (delimiter: ',')")
    delimiter: str = ','
    help_text = ''

    def __init__(self):
        self.response = HttpResponse(content_type='text/csv')
        self.writer = csv.writer(
            self.response,
            quoting=csv.QUOTE_ALL,
            delimiter=self.delimiter,
        )

    def writerow(self, row):
        return self.writer.writerow(row)

    def save(self, filename, user):
        self.response['Content-Disposition'] = f'attachment; filename="{slugify(filename)}.csv"'


class SemiCSVExportBackend(CSVExportBackend):
    id = 'scsv'
    verbose_name = _("CSV File (delimiter: ';')")
    delimiter = ';'
    help_text = ''
