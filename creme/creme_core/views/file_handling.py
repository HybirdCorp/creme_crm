################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from __future__ import annotations

import logging
from os.path import basename, join
from random import randint

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.files.base import File
from django.db import transaction
from django.forms import forms
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.urls.base import reverse

from creme.creme_core import http
from creme.creme_core.http import CremeJsonResponse
from creme.creme_core.models.file_ref import FileRef

from ..core.download import (
    DownLoadableFileField,
    FileFieldDownLoadRegistry,
    filefield_download_registry,
)
from ..utils.file_handling import FileCreator
from .generic import base

logger = logging.getLogger(__name__)

MAXINT = 100000


def handle_uploaded_file(f: File,
                         path: list[str] | None = None,
                         name: str | None = None,
                         max_length: int | None = None,
                         ) -> str:
    """Handle an uploaded file by a form and return the complete file's path."""
    def get_name(file: File) -> str:
        if hasattr(file, 'name'):
            name = file.name
        elif hasattr(file, '_name'):
            name = file._name
        else:
            name = f'file_{randint(0, MAXINT):08x}'

        if name.rpartition('.')[2].lower() not in settings.ALLOWED_EXTENSIONS:
            name = f'{name}.txt'

        return name

    dir_path_length = 1  # For the final '/'

    # TODO: add support for only one string?
    if path is None:
        relative_dir_path = ''
        dir_path = settings.MEDIA_ROOT
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


class RegisteredFileFieldDownloadView(base.ContentTypeRelatedMixin,
                                      base.CheckedView):
    """Serves files for (registered) FileFields."""
    pk_url_kwarg: str = 'pk'
    field_name_url_kwarg: str = 'field_name'

    dl_registry: FileFieldDownLoadRegistry = filefield_download_registry

    def get_dl_registry(self) -> FileFieldDownLoadRegistry:
        return self.dl_registry

    def get_dl_file_field(self) -> DownLoadableFileField:
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


class DropFileForm(forms.Form):
    upload = forms.FileField(required=True)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)


class DropFileView(base.CremeFormView):
    response_class = http.CremeJsonResponse
    max_path_length = 500
    form_class = DropFileForm
    fileref_url_kwarg = 'fileref_id'

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except PermissionDenied as exc:
            logger.exception(str(exc))
            return self.response_class({"error": {"message": str(exc)}}, status=403)
        except Exception as exc:
            logger.exception(str(exc))
            return self.response_class({"error": {"message": str(exc)}}, status=500)

    def handle_not_logged(self):
        return self.response_class({"error": "Not Logged In"}, status=403)

    def get(self, request, *args, **kwargs):
        instance = get_object_or_404(
            FileRef, pk=kwargs[self.fileref_url_kwarg],
        )

        return FileResponse(
            instance.filedata.open(),
            as_attachment=True,  # The downloaded file is named
            filename=instance.basename,
        )

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests: instantiate a form instance with the passed
        POST variables and then check if it's valid.
        """
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    @transaction.atomic
    def form_valid(self, form):
        filedata = form.cleaned_data["upload"]
        path = handle_uploaded_file(
            filedata,
            path=['uploads'],
            max_length=self.max_path_length,
        )

        file_ref = FileRef.objects.create(
            user=self.request.user,
            filedata=path,
            temporary=True,
        )

        return CremeJsonResponse({
            "url": reverse('creme_core__dropfile', args=(file_ref.pk,))
        })

    def form_invalid(self, form):
        return CremeJsonResponse({"error": {
            "message": '\n'.join(form.errors),
        }})
