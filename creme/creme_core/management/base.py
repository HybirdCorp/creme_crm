# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from django.core.management.base import BaseCommand


class CSVImportCommand(BaseCommand):
    """Base class for commands which import CSV files.
    Useful for CSV files that can not be easily managed by the generic visual
    CSV import system.

    Your can see an example of command in the file 'csv_import_example.py' in
    the same folder.
    """
    help = "Import data from a CSV file (base class)."
    # args = 'CSV filename'

    def add_arguments(self, parser):
        parser.add_argument(
            'args', metavar='csv_file', nargs='+',
            help='Path of the file to import',
        )

    def _read(self, filename, callback, delimiter=','):
        with open(filename, 'r') as csvfile:
            it = csv.reader(csvfile, delimiter=delimiter)

            try:
                header = next(it)
            except Exception:
                self.stderr.write('Void file ??!!')
                raise

            for i, line in enumerate(it, start=1):
                callback(i, line, {col: val for col, val in zip(header, line) if col})

    def _manage_line(self, idx, line, line_dict):
        """Override this method."""
        raise NotImplementedError

    def handle(self, *csv_filenames, **options):
        for csv_filename in csv_filenames:
            self._read(csv_filename, callback=self._manage_line, delimiter=';')
