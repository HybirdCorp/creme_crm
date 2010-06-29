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

from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.template.context import RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CustomField
from creme_core.views.generic import add_entity
from creme_core.utils import get_ct_or_404
from creme_core.entities_access.functions_for_permissions import get_view_or_die
from creme_core.constants import DROIT_MODULE_EST_ADMIN

from creme_config.forms.custom_fields import CustomFieldsCTAddForm, CustomFieldsAddForm, CustomFieldsEditForm
from creme_config.blocks import custom_fields_portal_block, custom_fields_block


ct_url     = '/creme_config/custom_fields/ct/%s'

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def add_ct(request):
    return add_entity(request, CustomFieldsCTAddForm, '/creme_config/custom_fields/portal/')

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def add(request, ct_id):
    ct = get_ct_or_404(ct_id)

    return add_entity(request, CustomFieldsAddForm,
                      url_redirect=ct_url % ct_id,
                      extra_initial={'ct': ct})

@login_required
@get_view_or_die('creme_config')
def portal(request):
    return render_to_response('creme_config/custom_fields/portal.html',
                              {},
                              context_instance=RequestContext(request))

@login_required
@get_view_or_die('creme_config')
def view(request, ct_id):
    ct = get_ct_or_404(ct_id)

    return render_to_response('creme_config/custom_fields/view.html',
                              {'content_type': ct},
                              context_instance=RequestContext(request))

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def edit(request, field_id):
    cfield = get_object_or_404(CustomField, pk=field_id)

    if request.POST :
        cfield_form = CustomFieldsEditForm(request.POST, instance=cfield)

        if cfield_form.is_valid():
            cfield_form.save()
            return HttpResponseRedirect(ct_url % cfield.content_type_id)
    else:
        cfield_form = CustomFieldsEditForm(instance=cfield)

    return render_to_response('creme_core/generics/form/edit.html',
                              {'form': cfield_form},
                              context_instance=RequestContext(request))

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def delete_ct(request):
    for field in CustomField.objects.filter(content_type=request.POST.get('id')):
        field.delete()

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")

    return HttpResponse()

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def delete(request):
    field = CustomField.objects.get(pk=request.POST.get('id'))
    field.delete()

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")

    return HttpResponse()

@login_required
@get_view_or_die('creme_config')
def reload_portal_block(request):
    return custom_fields_portal_block.detailview_ajax(request)

@login_required
@get_view_or_die('creme_config')
def reload_block(request, ct_id):
    return custom_fields_block.detailview_ajax(request, ct_id)
