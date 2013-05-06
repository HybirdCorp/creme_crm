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


class ImportBackend(object):
    """
    Base class defining backend used to import entities from listview.
    id: unique import backend identifier: the file extension matching this backend.
    verbose_name: defines the backend for the user, currently unused for import backends.
    help_text: a help text used in the import form.
    """
    id = "OVERLOAD ME"
    verbose_name = "OVERLOAD ME"
    help_text = "OVERLOAD ME"

    def next(self):
        """ Returns next line. """
        raise NotImplementedError


class ExportBackend(object):
    """
    Base class defining backend used to export entities from listview.
    Must define a django view response attribute: self.response.
    id: unique export backend identifier: the file extension matching this backend.
    verbose_name: defines the backend for the user, used in the select backend popup.
    help_text: currently unused.
    """
    id = "OVERLOAD ME"
    verbose_name = "OVERLOAD ME"
    help_text = "OVERLOAD ME"

    def writerow(self, row):
        """
        Appends a row.
        @param row: the row list
        """
        raise NotImplementedError

    def save(self, filename):
        """
        Saves the file
        @param filename: file name
        """
        raise NotImplementedError
