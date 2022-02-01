# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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

# import os
# import warnings
from os.path import basename, join
from random import randint
from typing import List, Optional

# from django.utils.translation import gettext as _
from django.conf import settings
from django.core.files.base import File
from django.http import FileResponse, Http404  # HttpResponse
from django.shortcuts import get_object_or_404

# from ..auth.decorators import login_required
from ..core.download import (
    DownLoadableFileField,
    FileFieldDownLoadRegistry,
    filefield_download_registry,
)
from ..utils.file_handling import FileCreator
from .generic import base

MAXINT = 100000


def handle_uploaded_file(f: File,
                         path: Optional[List[str]] = None,
                         name: Optional[str] = None,
                         max_length: Optional[int] = None,
                         ) -> str:
    """Handle an uploaded file by a form and return the complete file's path
    path has to be iterable
    """
    def get_name(file: File) -> str:
        if hasattr(file, 'name'):
            name = file.name
        elif hasattr(file, '_name'):
            name = file._name
        else:
            name = 'file_{:08x}'.format(randint(0, MAXINT))

        # if name.rpartition('.')[2] not in settings.ALLOWED_EXTENSIONS:
        if name.rpartition('.')[2].lower() not in settings.ALLOWED_EXTENSIONS:
            name = f'{name}.txt'

        return name

    dir_path_length = 1  # For the final '/'

    # TODO: add support for only one string?
    # if not hasattr(path, '__iter__'):
    if path is None:
        # relative_dir_path = 'upload'
        relative_dir_path = ''
        # dir_path = join(settings.MEDIA_ROOT, relative_dir_path)
        dir_path = settings.MEDIA_ROOT
        # dir_path_length += len(relative_dir_path)
    else:
        relative_dir_path = join(*path)
        dir_path = join(settings.MEDIA_ROOT, *path)

        # The storage uses '/' even on Windows.
        dir_path_length += len('/'.join(relative_dir_path))

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


# @login_required
# def download_file(request, location):
#     from mimetypes import guess_type
#
#     warnings.warn(
#         'The view download_file() is deprecated ; '
#         'use the class based-view RegisteredFileFieldDownloadView instead.',
#         DeprecationWarning
#     )
#
#     name_parts = location.replace('\\', '/').rpartition('/')[2].split('.')
#
#     if len(name_parts) == 1:  # Should not happen
#         ftype = 'text/plain'
#         name = name_parts[0]
#     else:
#         name = '.'.join(name_parts)
#         ftype = guess_type(name)[0] or 'application/octet-stream'
#
#     path = settings.MEDIA_ROOT + os.sep + location.replace('../', '').replace('..\\', '')
#
#     try:
#         with open(path, 'rb') as f:
#             data = f.read()
#     except IOError as e:
#         raise Http404(_('Invalid file')) from e
#
#     response = HttpResponse(data, content_type=ftype)
#     response['Content-Disposition'] = 'attachment; filename={}'.format(name.replace(' ', '_'))
#
#     return response


class RegisteredFileFieldDownloadView(base.ContentTypeRelatedMixin,
                                      base.CheckedView):
    """Serves files for (registered) FileFields."""
    pk_url_kwarg: str = 'pk'
    field_name_url_kwarg: str = 'field_name'

    dl_registry: FileFieldDownLoadRegistry = filefield_download_registry

    def get_dl_registry(self) -> FileFieldDownLoadRegistry:
        return self.dl_registry

    def get_dl_file_field(self) -> 'DownLoadableFileField':
        kwargs = self.kwargs
        instance = get_object_or_404(
            self.get_ctype().model_class(),
            pk=kwargs[self.pk_url_kwarg],
        )
        field_name = kwargs[self.field_name_url_kwarg]
        registry = self.get_dl_registry()

        try:
            dff = registry.get(
                user=self.request.user,
                instance=instance,
                field_name=field_name,
            )
        except registry.InvalidField as e:
            raise Http404(e) from e

        if not dff.file:
            raise Http404(
                f'The Field "{field_name}" on instance "{instance}" is empty.'
            )

        return dff

    def get(self, request, *args, **kwargs):
        dff = self.get_dl_file_field()

        # TODO ? (see django.views.static.serve() )
        # statobj = fullpath.stat()
        # if not was_modified_since(request.META.get('HTTP_IF_MODIFIED_SINCE'),
        #                           statobj.st_mtime, statobj.st_size):
        #     return HttpResponseNotModified()

        response = FileResponse(
            dff.file.open(),
            as_attachment=True,  # The downloaded file is named
            filename=dff.base_name,
        )

        # TODO ?
        # response['Last-Modified'] = http_date(statobj.st_mtime)

        return response
