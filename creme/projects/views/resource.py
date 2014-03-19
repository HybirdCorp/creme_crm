# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404
from django.http import HttpResponse

from creme.creme_core.utils import get_from_POST_or_404

from ..forms.resource import ResourceCreateForm, ResourceEditForm
from ..models import Resource
from .utils import _add_generic, _edit_generic


@login_required
@permission_required('projects')
#@permission_required('projects.add_resource') #resource not registered as CremeEntity
def add(request, task_id):
    return _add_generic(request, ResourceCreateForm, task_id, _(u"Allocation of a new resource"))

@login_required
@permission_required('projects')
def edit(request, resource_id):
    return _edit_generic(request, ResourceEditForm, resource_id, Resource, _(u"Edition of a resource"))

@login_required
@permission_required('projects')
def delete(request): #TODO: generic delete ??
    resource = get_object_or_404(Resource, pk=get_from_POST_or_404(request.POST, 'id'))

    request.user.has_perm_to_change_or_die(resource.task)
    #request.user.has_perm_to_delete_or_die(resource) #beware to change template if uncommented

    resource.delete()

    return HttpResponse()
