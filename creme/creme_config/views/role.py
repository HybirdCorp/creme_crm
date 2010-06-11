# -*- coding: utf-8 -*-

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
    return portal_roles(request)

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
