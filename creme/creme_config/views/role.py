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

from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.template.context import RequestContext
from django.core import serializers
from django.contrib.auth.decorators import login_required

from creme_core.models.authent_role import CremeRole
from creme_core.views.generic import add_entity
from creme_core.entities_access.functions_for_permissions import get_view_or_die
from creme_core.constants import DROIT_MODULE_EST_ADMIN

from creme_config.forms.role import RoleForm


@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def add(request):
    """
        @Permissions : Admin to creme_config app
    """
    return add_entity(request, RoleForm, '/creme_config/roles/portal/', 'creme_core/generics/form/add.html')

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def edit(request, role_id):
    """
        @Permissions : Admin to creme_config app
    """
    role = get_object_or_404(CremeRole, pk=role_id)

    if request.POST :
        #roleform = RoleEditForm(request.POST, instance=role)
        roleform = RoleForm(request.POST, instance=role)

        if roleform.is_valid():
            roleform.save()
            return HttpResponseRedirect('/creme_config/roles/portal/')
    else:
        #roleform = RoleEditForm(instance=role)
        roleform = RoleForm(instance=role)

    return render_to_response('creme_core/generics/form/edit.html', {'form': roleform},
                              context_instance=RequestContext(request))

@login_required
@get_view_or_die('creme_config')
def view(request, role_id):
    """
        @Permissions : Acces OR Admin to creme_config app
    """
    role = get_object_or_404(CremeRole, pk=role_id)

    return render_to_response('creme_config/roles/view_role.html',
                              {'object': role, 'path': '/creme_config/roles'},
                              context_instance=RequestContext(request))


@login_required
@get_view_or_die('creme_config')
def portal(request):
    """
        @Permissions : Acces OR Admin to creme_config app
    """
    top_roles = CremeRole.objects.filter(superieur=None)

    return render_to_response('creme_config/roles/portal.html', {'top_roles':top_roles},
                              context_instance=RequestContext(request))

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def delete(request, role_id):
    """
        @Permissions : Admin to creme_config app
    """
    role = get_object_or_404(CremeRole, pk=role_id)
    role.delete()
    return portal(request)#/!\ Url stay in browser's navigation bar

@login_required
@get_view_or_die('creme_config')
def ajax_get_direct_descendant(request):
    """
        @Permissions : Acces OR Admin to creme_config app
    """
    roleid = request.POST.get('key')

    if roleid:
        try:
            role = CremeRole.objects.get(pk=roleid)
            data = serializers.serialize('json', CremeRole.objects.filter(superieur=role))#, fields=fields)
        except CremeRole.DoesNotExist:
            return HttpResponse('', mimetype="text/javascript", status=400)

        return HttpResponse(data, mimetype="text/javascript", status=200)

    return HttpResponse('', mimetype="text/javascript", status=400)
