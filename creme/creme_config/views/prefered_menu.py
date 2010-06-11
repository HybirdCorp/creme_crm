# -*- coding: utf-8 -*-

from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.contrib.auth.decorators import login_required

from creme_core.entities_access.functions_for_permissions import get_view_or_die
from creme_core.constants import DROIT_MODULE_EST_ADMIN

from creme_config.forms.prefered_menu import PreferedMenuForm


@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def edit(request):
    if request.POST:
        form = PreferedMenuForm(None, request.POST)

        if form.is_valid():
            form.save()
            return HttpResponseRedirect('/creme_config/')
    else:
        form = PreferedMenuForm(user=None)

    return render_to_response('creme_core/generics/blockform/edit.html',
                              {'form': form},
                              context_instance=RequestContext(request))
