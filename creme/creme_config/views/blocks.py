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

from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.contrib.auth.decorators import login_required

from creme_core.models import BlockConfigItem
from creme_core.views.generic import add_entity
from creme_core.entities_access.functions_for_permissions import get_view_or_die
from creme_core.constants import DROIT_MODULE_EST_ADMIN

from creme_config.forms.blocks import BlocksAddForm, BlocksEditForm, BlocksPortalEditForm
from creme_config.blocks import blocks_config_block


portal_url = '/creme_config/blocks/portal/'

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def add(request):
    """
        @Permissions : Admin to creme_config app
    """
    return add_entity(request, BlocksAddForm, portal_url)

@login_required
@get_view_or_die('creme_config')
def portal(request):
    """
        @Permissions : Access OR Admin to creme_config app
    """
    return render_to_response('creme_config/blocks_portal.html',
                              {},
                              context_instance=RequestContext(request))

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def _edit(request, ct_id, form_class):
    ct_id = int(ct_id)

    if not ct_id:
        bci = BlockConfigItem.objects.filter(content_type=None)
    else:
        bci = BlockConfigItem.objects.filter(content_type__id=ct_id)

    bci = bci.order_by('order')

    if not bci:
        raise Http404 #bof bof

    if request.POST:
        blocks_form = form_class(bci, request.POST)

        if blocks_form.is_valid():
            blocks_form.save()
            return HttpResponseRedirect(portal_url)
    else:
        blocks_form = form_class(block_config_items=bci, initial={'ct_id': ct_id})

    return render_to_response('creme_core/generics/blockform/edit.html',
                              {'form': blocks_form},
                              context_instance=RequestContext(request))

def edit(request, ct_id):
    return _edit(request, ct_id, BlocksEditForm)

def edit_portal(request, ct_id):
    return _edit(request, ct_id, BlocksPortalEditForm)

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def delete(request):
    ct_id = request.POST.get('id')
    if not ct_id: #default config can't be deleted
        raise Http404 #bof

    BlockConfigItem.objects.filter(content_type__id=ct_id).delete()
    return HttpResponse()

@login_required
@get_view_or_die('creme_config')
def reload_block(request):
    return blocks_config_block.detailview_ajax(request)
