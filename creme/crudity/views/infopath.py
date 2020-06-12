# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

from django.http import Http404

from creme.creme_core.auth.decorators import (
    login_required,
    permission_required,
)

from .. import registry
from ..backends.models import CrudityBackend
from ..builders.infopath import InfopathFormBuilder


@login_required
@permission_required('crudity')
def create_form(request, subject):
    subject = CrudityBackend.normalize_subject(subject)
    backend = None

    for fetcher in registry.crudity_registry.get_fetchers():
        input = fetcher.get_input('infopath', 'create')
        if input is not None:
            backend = input.get_backend(subject)
            break

    if backend is None:
        raise Http404('This backend is not registered')

    return InfopathFormBuilder(request, backend).render()
