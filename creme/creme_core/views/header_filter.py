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

#from logging import debug

from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render_to_response
from django.template.context import RequestContext

from creme_core.forms.header_filter import HeaderFilterForm
from creme_core.views.generic import add_entity
from creme_core.models.header_filter import HeaderFilter
from creme_core.entities_access.functions_for_permissions import delete_object_or_die


@login_required
def add(request, content_type_id, extra_template_dict=None):
    """
        @Permissions : to be set
    """
    ct_entity = get_object_or_404(ContentType, pk=content_type_id)

    try:
        callback_url = ct_entity.model_class().get_lv_absolute_url()
    except AttributeError:
        callback_url = '/'

    return add_entity(request, HeaderFilterForm, callback_url,
                      template='creme_core/header_filters.html',
                      extra_initial={'content_type_id': content_type_id},
                      extra_template_dict=extra_template_dict or {})

@login_required
def edit(request, header_filter_id):
    hf           = get_object_or_404(HeaderFilter, pk=header_filter_id)
    callback_url = hf.entity_type.model_class().get_lv_absolute_url()

    if request.POST:
        hf_form = HeaderFilterForm(request.POST, instance=hf)
        if hf_form.is_valid():
            hf_form.save()
            return HttpResponseRedirect(callback_url)
    else:
        hf_form = HeaderFilterForm(instance=hf)

    return render_to_response('creme_core/header_filters.html',
                              {'form': hf_form},
                              context_instance=RequestContext(request))

@login_required
def delete(request, header_filter_id, js=0):
    hf           = get_object_or_404(HeaderFilter, pk=header_filter_id)
    callback_url = hf.entity_type.model_class().get_lv_absolute_url()
    return_msg   = u'Vue supprimée avec succès'
    status       = 200

    if hf.is_custom:
        die_status = delete_object_or_die(request, hf)
        if die_status:
            if not js:
                return die_status
            else:
                return_msg = u'Permission refusée'
                status = 400
        else:
            hf.delete()
    else:
        return_msg = u'Cette vue ne peut être effacée'
        status = 400

    if js:
        return HttpResponse(return_msg, mimetype="text/javascript", status=status)

    return HttpResponseRedirect(callback_url)
