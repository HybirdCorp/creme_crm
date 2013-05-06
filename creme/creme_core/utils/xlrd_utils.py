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

import xlrd


class XlrdReader(object):
    def __init__(self, filedata=None, file_contents=None):
        sheet = xlrd.open_workbook(filename=getattr(filedata, 'path', filedata),
                                   file_contents=file_contents).sheet_by_index(0)
        self._calc = ([self.get_cell_value(cell) for cell in sheet.row(row_number)] for row_number in xrange(sheet.nrows))

    def __iter__(self):
        return self

    def next(self):
        return self._calc.next()

    def get_cell_value(self, cell):
        """
        cell types: 0: empty
                    1: text
                    2: numbers
        """
        value = cell.value
        if cell.ctype == 2 and int(value) == float(value):
            return int(value)
        return value
