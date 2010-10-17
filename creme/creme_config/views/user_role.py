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

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template.context import RequestContext
from django.contrib.auth.decorators import login_required

from creme_core.models import UserRole
from creme_core.views.generic import add_entity
from creme_core.entities_access.functions_for_permissions import get_view_or_die
from creme_core.constants import DROIT_MODULE_EST_ADMIN
from creme_core.utils import get_from_POST_or_404

from creme_config.forms.user_role import UserRoleCreateForm, UserRoleEditForm, AddCredentialsForm


PORTAL_URL = '/creme_config/role/portal/'

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def add(request):
    return add_entity(request, UserRoleCreateForm, PORTAL_URL, 'creme_core/generics/form/add.html')

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def edit(request, role_id):
    role = get_object_or_404(UserRole, pk=role_id)

    if request.method == 'POST':
        roleform = UserRoleEditForm(request.POST, instance=role)

        if roleform.is_valid():
            roleform.save()
            return HttpResponseRedirect(PORTAL_URL)
    else:
        roleform = UserRoleEditForm(instance=role)

    return render_to_response('creme_core/generics/form/edit.html',
                              {'form': roleform},
                              context_instance=RequestContext(request))

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def add_credentials(request, role_id):
    role = get_object_or_404(UserRole, pk=role_id)

    if request.method == 'POST':
        roleform = AddCredentialsForm(role, request.POST)

        if roleform.is_valid():
            roleform.save()
            return HttpResponseRedirect(PORTAL_URL)
    else:
        roleform = AddCredentialsForm(role)

    return render_to_response('creme_core/generics/blockform/edit.html',
                              {'form': roleform},
                              context_instance=RequestContext(request))

@login_required
@get_view_or_die('creme_config')
def portal(request):
    return render_to_response('creme_config/user_role_portal.html', {},
                              context_instance=RequestContext(request))

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def delete(request):
    role = get_object_or_404(UserRole, pk=get_from_POST_or_404(request.POST, 'id'))
    role.delete() #TODO: overload to udpate credentials

    return HttpResponse()
