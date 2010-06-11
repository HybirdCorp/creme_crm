# -*- coding: utf-8 -*-

from logging import debug #

from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.decorators import login_required

from creme_core.models import RelationType
from creme_core.views.generic import add_entity
from creme_core.entities_access.functions_for_permissions import get_view_or_die
from creme_core.constants import DROIT_MODULE_EST_ADMIN

from creme_config.forms.relation_type import RelationTypeCreateForm, RelationTypeEditForm
from creme_config.blocks import relation_types_block


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
def delete(request, relation_type_id):
    """
        @Permissions : Admin to creme_config app
    """
    relation_type = get_object_or_404(RelationType, pk=relation_type_id)

    relation_type.delete()

    return HttpResponseRedirect(portal_url)

@login_required
@get_view_or_die('creme_config')
def reload_block(request):
    return relation_types_block.detailview_ajax(request)
