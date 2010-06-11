# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.decorators import login_required

from creme_core.entities_access.functions_for_permissions import add_view_or_die, get_view_or_die
from creme_core.views.generic import add_entity, edit_entity, view_entity_with_template, list_view

from persons.models import Organisation
from persons.forms.organisation import OrganisationForm
from persons.blocks import managers_block, employees_block


@login_required
@get_view_or_die('persons')
@add_view_or_die(ContentType.objects.get_for_model(Organisation), None, 'persons')
def add(request):
    return add_entity(request, OrganisationForm, template="persons/add_organisation_form.html")

def edit(request, organisation_id):
    return edit_entity(request, organisation_id, Organisation, OrganisationForm, 'persons', template='persons/edit_organisation_form.html')

@login_required
@get_view_or_die('persons')
def detailview(request, organisation_id):
    return view_entity_with_template(request, organisation_id, Organisation, '/persons/organisation', 'persons/view_organisation.html')

@login_required
@get_view_or_die('persons')
def listview(request):
    return list_view(request, Organisation, extra_dict={'add_url': '/persons/organisation/add'})

@login_required
def reload_managers(request, organisation_id):
    return managers_block.detailview_ajax(request, organisation_id)

@login_required
def reload_employees(request, organisation_id):
    return employees_block.detailview_ajax(request, organisation_id)
