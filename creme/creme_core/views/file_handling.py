# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from mimetypes import guess_type
import os
from os.path import basename, join
from random import randint

from django.conf import settings
from django.http import HttpResponse, Http404
from django.utils.translation import ugettext as _

from ..auth.decorators import login_required
from ..utils.file_handling import FileCreator


MAXINT = 100000


def handle_uploaded_file(f, path=None, name=None, max_length=None):
    """Handle an uploaded file by a form and return the complete file's path
    path has to be iterable
    """
    def get_name(file):
        if hasattr(file, 'name'):
            name = file.name
        elif hasattr(file, '_name'):
            name = file._name
        else:
            name = 'file_{:08x}'.format(randint(0, MAXINT))

        if name.rpartition('.')[2] not in settings.ALLOWED_EXTENSIONS:
            name = '{}.txt'.format(name)

        return name

    dir_path_length = 1  # For the final '/'

    if not hasattr(path, '__iter__'):  # TODO: path is None  (or add support for only one string)
        relative_dir_path = 'upload'
        dir_path = join(settings.MEDIA_ROOT, relative_dir_path)
        dir_path_length += len(relative_dir_path)
    else:
        relative_dir_path = join(*path)
        dir_path = join(settings.MEDIA_ROOT, *path)
        dir_path_length += len('/'.join(relative_dir_path))  # The storage uses '/' even on Windows.

    if not name:
        name = get_name(f)

    if max_length:
        max_length -= dir_path_length

        if max_length <= 0:
            raise ValueError('The max length is too small.')

    final_path = FileCreator(dir_path=dir_path, name=name, max_length=max_length).create()

    with open(final_path, 'wb', 0o755) as destination:
        for chunk in f.chunks():
            destination.write(chunk)

    return join(relative_dir_path, basename(final_path))


@login_required
def download_file(request, location):
    name_parts = location.replace('\\', '/').rpartition('/')[2].split('.')

    if len(name_parts) == 1:  # Should not happen
        ftype = 'text/plain'
        name = name_parts[0]
    else:
        name = '.'.join(name_parts)
        ftype = guess_type(name)[0] or 'application/octet-stream'

    path = settings.MEDIA_ROOT + os.sep + location.replace('../', '').replace('..\\', '')

    try:
        with open(path, 'rb') as f:
            data = f.read()
    except IOError as e:
        raise Http404(_('Invalid file')) from e

    response = HttpResponse(data, content_type=ftype)
    response['Content-Disposition'] = 'attachment; filename={}'.format(name.replace(' ', '_'))

    return response
