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

from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import HttpResponse

from creme_core.entities_access.functions_for_permissions import edit_object_or_die
from creme_core.utils import get_from_POST_or_404

from projects.forms.resource import ResourceForm
from projects.views.utils import _add_generic, _edit_generic
from projects.models import Resource


def add(request, task_id):
    return _add_generic(request, ResourceForm, task_id, _(u"Allocation of a new resource"))

def edit(request, resource_id):
    """
        @Permissions : Acces or Admin to project & Edit on current object
    """
    return _edit_generic(request, ResourceForm, resource_id, Resource, _(u"Edition of a resource"))

@login_required
def delete(request):
    resource   = get_object_or_404(Resource, pk=get_from_POST_or_404(request.POST, 'id'))
    die_status = edit_object_or_die(request, resource.task)

    if die_status:
        return die_status

    resource.delete()

    return HttpResponse()
