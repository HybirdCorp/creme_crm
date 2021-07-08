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

from django.utils.translation import gettext_lazy as _

from ..utils.xlrd_utils import XlrdReader
from .base import ImportBackend


class XLSImportBackend(XlrdReader, ImportBackend):
    id = 'xls'
    verbose_name = _('XLS File')
    help_text = _(
        'XLS is a file extension for a spreadsheet file format created by '
        'Microsoft for use with Microsoft Excel (Excel 97-2003 Workbook).'
    )


class XLSXImportBackend(XlrdReader, ImportBackend):
    id = 'xlsx'
    verbose_name = _('XLSX File')
    help_text = _('XLSX file extension introduced by Microsoft Excel 2007.')
