# -*- coding: utf-8 -*-

from logging import debug

from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render_to_response
from django.template.context import RequestContext

from creme_core.models.authent import CremeAppTypeDroit, CremeAppDroit
from creme_core.views.generic import add_entity
from creme_core.entities_access.functions_for_permissions import get_view_or_die
from creme_core.registry import creme_registry
from creme_core.constants import DROIT_MODULE_EST_ADMIN

from creme_config.forms.app_credential import CremeAppDroitForm
from creme_config.blocks import app_credentials_block


portal_url = '/creme_config/roles/app_credential/portal/'

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def add(request):
    """
        @Permissions : Admin to creme_config app
    """
    return add_entity(request, CremeAppDroitForm, portal_url, 'creme_core/generics/form/add.html')

@login_required
@get_view_or_die('creme_config')
def portal(request):
    """
        @Permissions : Access OR Admin to creme_config app
    """
    return render_to_response('creme_config/roles/app_credential_portal.html',
                              {},
                              context_instance=RequestContext(request))

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def delete(request, app_cred_id):
    """
        @Permissions : Admin to creme_config app
    """
    app_cred = get_object_or_404(CremeAppDroit, pk=app_cred_id)
    app_cred.delete()

    return HttpResponseRedirect(portal_url)

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def generate_all(request):
    """
        @Permissions : Admin to creme_config app
    """
#    for app in creme_registry.get_iter_app():
    for app in creme_registry._apps: #beurk
        for credential in CremeAppTypeDroit.objects.all():
            try:
                debug('app:%s', app)
                debug('credential:%s', credential)
                CremeAppDroit.objects.get_or_create(type_droit=credential, name_app=app)
            except Exception, e:
                debug('Exception CremeAppDroit : %s', e)

    return HttpResponseRedirect(portal_url)

@login_required
@get_view_or_die('creme_config')
def reload_block(request):
    return app_credentials_block.detailview_ajax(request)
