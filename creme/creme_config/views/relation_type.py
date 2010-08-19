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

from logging import debug #

from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.decorators import login_required

from creme_core.models import RelationType
from creme_core.views.generic import add_entity
from creme_core.entities_access.functions_for_permissions import get_view_or_die
from creme_core.constants import DROIT_MODULE_EST_ADMIN

from creme_config.forms.relation_type import RelationTypeCreateForm, RelationTypeEditForm


portal_url = '/creme_config/relation_type/portal/'

@login_required
@get_view_or_die('creme_config')
def portal(request):
    """
        @Permissions : Acces OR Admin to creme_config app
    """
    return render_to_response('creme_config/relation_type_portal.html',
                              {},
                              context_instance=RequestContext(request))

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def add(request):
    return add_entity(request, RelationTypeCreateForm, portal_url)

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def edit(request, relation_type_id):
    relation_type = get_object_or_404(RelationType, pk=relation_type_id)

    if not relation_type.is_custom:
        raise Http404("Can't edit a standard RelationType") #TODO: 403 instead ?

    if request.POST:
        form = RelationTypeEditForm(relation_type, request.POST)

        if form.is_valid():
            form.save()
            return HttpResponseRedirect(portal_url)
    else:
        form = RelationTypeEditForm(instance=relation_type)

    return render_to_response('creme_core/generics/blockform/edit.html',
                              {'form': form},
                              context_instance=RequestContext(request))

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def delete(request):
    """
        @Permissions : Admin to creme_config app
    """
    relation_type = get_object_or_404(RelationType, pk=request.POST.get('id'))

    if not relation_type.is_custom:
        raise Http404("Can't delete a standard RelationType") #TODO: 403 instead ?

    relation_type.delete()

    return HttpResponse()
