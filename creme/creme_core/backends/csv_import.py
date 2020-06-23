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

import csv

from django.utils.translation import gettext_lazy as _

from .base import ImportBackend


class CSVImportBackend(ImportBackend):
    id = 'csv'
    verbose_name = _('CSV File')
    help_text = _(
        'A CSV file contains the fields values of an entity on each line, '
        'separated by commas or semicolons and each one can be surrounded by quotation marks " '
        '(to protect a value containing a comma for example).'
    )

    def __init__(self, f):
        super().__init__(f)
        dialect = csv.Sniffer().sniff(f.read(100 * 1024))
        f.seek(0)

        self.reader = csv.reader(f, dialect=dialect)

    def __next__(self):
        return next(self.reader)
