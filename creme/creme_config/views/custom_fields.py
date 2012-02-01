# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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
from django.shortcuts import render, get_object_or_404
from django.template.context import RequestContext
from django.contrib.auth.decorators import login_required, permission_required

from creme_core.models import CustomField
from creme_core.views.generic import add_model_with_popup, edit_model_with_popup
from creme_core.utils import get_ct_or_404, get_from_POST_or_404, jsonify

from creme_config.forms.custom_fields import CustomFieldsCTAddForm, CustomFieldsAddForm, CustomFieldsEditForm
from creme_config.blocks import custom_fields_block


@login_required
@permission_required('creme_config.can_admin')
def add_ct(request):
    return add_model_with_popup(request, CustomFieldsCTAddForm)

@login_required
@permission_required('creme_config.can_admin')
def add(request, ct_id):
    return add_model_with_popup(request, CustomFieldsAddForm,
                                initial={'ct': get_ct_or_404(ct_id)}
                               )

@login_required
@permission_required('creme_config')
def portal(request):
    return render(request, 'creme_config/custom_fields/portal.html')

@login_required
@permission_required('creme_config')
def view(request, ct_id):
    ct = get_ct_or_404(ct_id)

    return render(request, 'creme_config/custom_fields/view.html', {'content_type': ct})

@login_required
@permission_required('creme_config.can_admin')
def edit(request, field_id):
    return edit_model_with_popup(request, {'pk': field_id}, CustomField, CustomFieldsEditForm)

@login_required
@permission_required('creme_config.can_admin')
def delete_ct(request):
    for field in CustomField.objects.filter(content_type=get_from_POST_or_404(request.POST, 'id')):
        field.delete()

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")

    return HttpResponse()

@login_required
@permission_required('creme_config.can_admin')
def delete(request):
    field = CustomField.objects.get(pk=get_from_POST_or_404(request.POST, 'id'))
    field.delete()

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")

    return HttpResponse()

@jsonify
@login_required
@permission_required('creme_config.can_admin')
def reload_block(request, ct_id):
    context = RequestContext(request)
    context['content_type'] = get_ct_or_404(ct_id)

    return [(custom_fields_block.id_, custom_fields_block.detailview_display(context))]
