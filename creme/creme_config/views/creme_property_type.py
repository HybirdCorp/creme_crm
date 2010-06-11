# -*- coding: utf-8 -*-

from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.template.context import RequestContext
from django.contrib.auth.decorators import login_required

from creme_core.models import CremePropertyType
from creme_core.views.generic import add_entity
from creme_core.constants import DROIT_MODULE_EST_ADMIN
from creme_core.entities_access.functions_for_permissions import get_view_or_die

from creme_config.forms.creme_property_type import CremePropertyTypeEditForm, CremePropertyTypeAddForm
from creme_config.blocks import property_types_block


portal_url = '/creme_config/property_type/portal/'

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def add(request):
    """
        @Permissions : Admin to creme_config app
    """
    return add_entity(request, CremePropertyTypeAddForm, portal_url, 'creme_core/generics/form/add.html')

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def edit(request, property_type_id):
    """
        @Permissions : Admin to creme_config app
    """
    property_type = get_object_or_404(CremePropertyType, pk=property_type_id)

    if request.POST :
        property_type_form = CremePropertyTypeEditForm(property_type, request.POST)

        if property_type_form.is_valid():
            property_type_form.save()
            return HttpResponseRedirect(portal_url)
    else:
        property_type_form = CremePropertyTypeEditForm(property_type)

    return render_to_response('creme_core/generics/form/edit.html',
                              {'form': property_type_form},
                              context_instance=RequestContext(request))

@login_required
@get_view_or_die('creme_config')
def portal(request):
    """
        @Permissions : Acces OR Admin to creme_config app
    """
    return render_to_response('creme_config/property_type_portal.html',
                              {},
                              context_instance=RequestContext(request))

#TODO: PropertyLabel not deleted ???
@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def delete(request, property_type_id):
    """
        @Permissions : Admin to creme_config app
    """
    property_type = get_object_or_404(CremePropertyType, pk=property_type_id)
    property_type.delete()
    return HttpResponseRedirect(portal_url)

@login_required
@get_view_or_die('creme_config')
def reload_block(request):
    return property_types_block.detailview_ajax(request)
