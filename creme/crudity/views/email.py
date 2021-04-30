# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from django.conf import settings
from django.http import Http404, HttpResponse
from django.template.loader import render_to_string

from creme.creme_core.auth.decorators import (
    login_required,
    permission_required,
)
from creme.creme_core.utils.secure_filename import secure_filename

from .. import registry
from ..backends.models import CrudityBackend


@login_required
@permission_required('crudity')
def download_email_template(request, subject):
    subject = CrudityBackend.normalize_subject(subject)
    backend = None

    input = registry.crudity_registry.get_fetcher('email').get_input('raw', 'create')
    if input is not None:
        backend = input.get_backend(subject)

    if backend is None:
        raise Http404('This backend is not registered')

    response = HttpResponse(
        render_to_string(
            # TODO: rename crudity/create_email_template.eml ??
            'crudity/create_email_template.html',
            {
                'backend': backend,
                'contact': request.user.linked_contact,
                'to':      settings.CREME_GET_EMAIL,
            },
            request=request,
        ),
        # content_type='application/vnd.sealed.eml',
        headers={
            'Content-Type': 'application/vnd.sealed.eml',
            'Content-Disposition': f'attachment; filename="{secure_filename(subject)}.eml"',
        },
    )

    # response['Content-Disposition'] = 'attachment; filename={}.eml'.format(
    #     secure_filename(subject)
    # )

    return response
