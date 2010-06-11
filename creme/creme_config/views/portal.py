# -*- coding: utf-8 -*-

from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.template import RequestContext

from creme_core.entities_access.functions_for_permissions import get_view_or_die

from creme_config.registry import config_registry


@login_required
@get_view_or_die('creme_config')
def portal(request):
    """
        @Permissions : Acces OR Admin to creme_config app
    """
    return render_to_response('creme_config/portal.html',
                              {'app_configs': config_registry.apps()},
                              context_instance=RequestContext(request))
