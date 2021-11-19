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

from os.path import basename, join

from django.conf import settings
from django.http import HttpResponseRedirect
from django.template.defaultfilters import slugify
from django.utils.translation import gettext_lazy as _

from ..models import FileRef
from ..utils.file_handling import FileCreator
from ..utils.xlwt_utils import XlwtWriter
from .base import ExportBackend


class XLSExportBackend(ExportBackend):
    id = 'xls'
    verbose_name = _('XLS File')
    help_text = ''
    # dir_parts = ('xls',)  # Sub-directory under {settings.MEDIA_ROOT}/upload
    dir_parts = ('xls',)  # Sub-directory under settings.MEDIA_ROOT

    def __init__(self, encoding='utf-8'):
        super().__init__()
        # self.dir_path = join(settings.MEDIA_ROOT, 'upload', *self.dir_parts)
        self.dir_path = join(settings.MEDIA_ROOT, *self.dir_parts)
        self.writer = XlwtWriter(encoding=encoding)

    def save(self, filename, user):
        name = f'{slugify(filename)}.{self.id}'
        path = FileCreator(dir_path=self.dir_path, name=name).create()
        fileref = FileRef.objects.create(
            user=user,
            basename=name,
            # filedata='upload/{}/{}'.format(
            filedata='{}/{}'.format(
                '/'.join(self.dir_parts),
                basename(path),
            ),
        )
        self.response = HttpResponseRedirect(fileref.get_download_absolute_url())
        self.writer.save(path)

    def writerow(self, row):
        self.writer.writerow(row)
