# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

from datetime import datetime

# from xlrd import XL_CELL_EMPTY, XL_CELL_TEXT, XL_CELL_ERROR, XL_CELL_BLANK
from xlrd import (
    XL_CELL_BOOLEAN,
    XL_CELL_DATE,
    XL_CELL_NUMBER,
    open_workbook,
    xldate_as_tuple,
)


class XlCTypeHandler:
    """
        class handling cell types:
        XL_CELL_EMPTY (0): empty string ''.
        XL_CELL_TEXT (1): string.
        XL_CELL_NUMBER (2): float (number).
        XL_CELL_DATE (3): float (date).
        XL_CELL_BOOLEAN (4): boolean (0, 1).
        XL_CELL_ERROR (5): int representing internal Excel codes;
            for a text representation, refer to the supplied
            dictionary error_text_from_code.
        XL_CELL_BLANK (6): empty string ''.
            Note: this type will appear only when
            open_workbook(..., formatting_info=True) is used.
        """
    def __init__(self, book):
        self.datemode = book.datemode
        self._ctype_handlers = {
            # XL_CELL_EMPTY: self.default_handler,
            # XL_CELL_TEXT: self.default_handler,
            XL_CELL_NUMBER: self.number_handler,
            XL_CELL_DATE: self.date_handler,
            XL_CELL_BOOLEAN: self.boolean_handler,
            # XL_CELL_ERROR: self.default_handler,
            # XL_CELL_BLANK: self.default_handler,
        }

    def default_handler(self, cell):
        return cell.value

    def number_handler(self, cell):
        value = cell.value
        int_value = int(value)
        return int_value if int_value == value else value

    def date_handler(self, cell):
        return datetime(*xldate_as_tuple(cell.value, self.datemode))

    def boolean_handler(self, cell):
        return bool(cell.value)

    def handle_cell(self, cell):
        return self._ctype_handlers.get(cell.ctype, self.default_handler)(cell)


class XlrdReader:
    def __init__(self, filedata=None, file_contents=None, sheet_index=0):
        book = self.book = open_workbook(filename=getattr(filedata, 'path', filedata),
                                         file_contents=file_contents)
        sheet = self.sheet = book.sheet_by_index(sheet_index)

        cell_parser = XlCTypeHandler(book)
        parse = cell_parser.handle_cell

        self._calc = (
            [parse(cell) for cell in sheet.row(row_number)]
            for row_number in range(sheet.nrows)
        )

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._calc)
