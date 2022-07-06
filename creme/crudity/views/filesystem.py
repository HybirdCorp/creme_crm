################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2017-2022  Hybird
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

import configparser
from io import StringIO

from django.contrib.auth import get_user_model
from django.http import Http404, HttpResponse

from creme.creme_core.auth.decorators import (
    login_required,
    permission_required,
)
from creme.creme_core.utils.secure_filename import secure_filename

from .. import registry
from ..utils import is_sandbox_by_user


@login_required
@permission_required('crudity')
def download_ini_template(request, subject):
    # subject = CrudityBackend.normalize_subject(subject)  ??
    backend = None
    input = registry.crudity_registry.get_fetcher('filesystem').get_input('ini', 'create')

    if input is not None:
        backend = input.get_backend(subject)

    if backend is None:
        raise Http404('This backend is not registered')

    ini = configparser.RawConfigParser()
    ini.add_section('head')
    ini.set('head', 'action', subject)

    if is_sandbox_by_user():
        ini.set('head', 'username', getattr(request.user, get_user_model().USERNAME_FIELD))

    ini.add_section('body')
    for k, v in backend.body_map.items():
        ini.set('body', k, v)

    buffer = StringIO()
    ini.write(buffer)

    return HttpResponse(
        buffer.getvalue(),
        headers={
            'Content-Type': 'text/plain',
            'Content-Disposition': f'attachment; filename="{secure_filename(subject)}.ini"',
        },
    )
