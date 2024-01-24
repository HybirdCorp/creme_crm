################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024  Hybird
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

from django.utils.translation import gettext_lazy as _
from openpyxl import load_workbook

from .base import ImportBackend


class XLSXImportBackend(ImportBackend):
    id = 'xlsx'
    verbose_name = _('XLSX File')
    help_text = _('XLSX file created by Microsoft Excel 2010 ®.')

    def __init__(self, f):
        super().__init__(f=f)
        self._workbook = wb = load_workbook(
            filename=getattr(f, 'path', f),
            read_only=True,
        )
        self._rows = wb.active.rows

    def __next__(self):
        return [td.value for td in next(self._rows)]
