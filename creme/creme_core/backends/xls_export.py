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

from os.path import join, exists
from os import makedirs

from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponseRedirect
from django.template.defaultfilters import slugify

from ..utils.xlwt_utils import XlwtWriter

from .base import ExportBackend


class XLSExportBackend(XlwtWriter, ExportBackend):
    id = 'xls'
    verbose_name = _(u'XLS File')
    help_text = ''

    def __init__(self, encoding="utf-8"):
        self.dir_path = dir_path = join(settings.MEDIA_ROOT, 'upload', 'xls')
        if not exists(dir_path):
            makedirs(dir_path)
        super(XLSExportBackend, self).__init__(encoding="utf-8")

    def save(self, filename):
        filename = '%s.%s' % (slugify(filename), self.id)
        self.response = HttpResponseRedirect('/download_file/upload/xls/%s' % filename)
        super(XLSExportBackend, self).save(join(self.dir_path, filename))
