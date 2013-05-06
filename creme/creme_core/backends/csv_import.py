# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013  Hybird
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

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.utils.unicode_csv import UnicodeReader

from .base import ImportBackend


class CSVImportBackend(UnicodeReader, ImportBackend):
    id = 'csv'
    verbose_name = _(u'CSV File')
    help_text = _(u'A CSV file contains the fields values of an entity on each line, '
                  'separated by commas or semicolons and each one can be surrounded by quotation marks " '
                  '(to protect a value containing a comma for example).'
                  )
