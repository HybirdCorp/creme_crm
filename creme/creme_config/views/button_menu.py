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
from django.contrib.auth.decorators import login_required, permission_required

from creme_core.models import ButtonMenuItem
from creme_core.views.generic import add_entity
from creme_core.utils import get_from_POST_or_404

from creme_config.forms.button_menu import ButtonMenuAddForm, ButtonMenuEditForm


portal_url = '/creme_config/button_menu/portal/'

@login_required
@permission_required('creme_config.can_admin')
def add(request):
    return add_entity(request, ButtonMenuAddForm, portal_url)

@login_required
@permission_required('creme_config')
def portal(request):
    return render_to_response('creme_config/button_menu_portal.html',
                              {},
                              context_instance=RequestContext(request))

@login_required
@permission_required('creme_config.can_admin')
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
@permission_required('creme_config.can_admin')
def delete(request):
    ct_id = get_from_POST_or_404(request.POST, 'id')

    #Set a constant to recognize default config, because POST QueryDict can be empty ?
    if not ct_id: #default config can't be deleted
        raise Http404 #bof

    ButtonMenuItem.objects.filter(content_type=ct_id).delete()

    return HttpResponse()
