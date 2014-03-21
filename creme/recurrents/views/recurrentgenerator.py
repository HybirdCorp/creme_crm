# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views.generic import view_entity, list_view, edit_entity

from ..forms.recurrentgenerator import RecurrentGeneratorWizard, RecurrentGeneratorEditForm
from ..models import RecurrentGenerator


_wizard = RecurrentGeneratorWizard()

@login_required
@permission_required('recurrents')
@permission_required('recurrents.add_recurrentgenerator')
def add(request):
    return _wizard(request)

@login_required
@permission_required('recurrents')
def edit(request, generator_id):
    return edit_entity(request, generator_id, RecurrentGenerator, RecurrentGeneratorEditForm)

@login_required
@permission_required('recurrents')
def listview(request):
    return list_view(request, RecurrentGenerator, extra_dict={'add_url': '/recurrents/generator/add'})

@login_required
@permission_required('recurrents')
def detailview(request, generator_id):
    return view_entity(request, generator_id, RecurrentGenerator,
                       '/recurrents/generator', 'recurrents/view_generator.html',
                      )
