# -*- coding: utf-8 -*-

from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.contrib.auth.decorators import login_required

from creme_core.models import ButtonMenuItem
from creme_core.views.generic import add_entity
from creme_core.entities_access.functions_for_permissions import get_view_or_die
from creme_core.constants import DROIT_MODULE_EST_ADMIN

from creme_config.forms.button_menu import ButtonMenuAddForm, ButtonMenuEditForm
from creme_config.blocks import button_menu_block


portal_url = '/creme_config/button_menu/portal/'

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def add(request):
    """
        @Permissions : Admin to creme_config app
    """
    return add_entity(request, ButtonMenuAddForm, portal_url)

@login_required
@get_view_or_die('creme_config')
def portal(request):
    """
        @Permissions : Access OR Admin to creme_config app
    """
    return render_to_response('creme_config/button_menu_portal.html',
                              {},
                              context_instance=RequestContext(request))

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def edit(request, ct_id):
    ct_id = int(ct_id)

    if not ct_id:
        bmi = ButtonMenuItem.objects.filter(content_type=None)
    else:
        bmi = ButtonMenuItem.objects.filter(content_type__id=ct_id)

    bmi.order_by('order')

    if not bmi:
        raise Http404 #bof bof

    if request.method == 'POST':
        buttons_form = ButtonMenuEditForm(bmi, ct_id, request.POST)

        if buttons_form.is_valid():
            buttons_form.save()
            return HttpResponseRedirect(portal_url)
    else:
        buttons_form = ButtonMenuEditForm(bmi, ct_id)

    return render_to_response('creme_core/generics/blockform/edit.html',
                              {'form': buttons_form},
                              context_instance=RequestContext(request))

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def delete(request):
    ct_id = request.POST.get('id')
    #Set a constant to recognize default config, because POST QueryDict can be empty ?
    if not ct_id: #default config can't be deleted
        raise Http404 #bof

    ButtonMenuItem.objects.filter(content_type__id=ct_id).delete()
    return HttpResponse()

@login_required
@get_view_or_die('creme_config')
def reload_block(request):
    return button_menu_block.detailview_ajax(request)

