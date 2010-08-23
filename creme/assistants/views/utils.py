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

from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required

from creme_core.entities_access.functions_for_permissions import edit_object_or_die
from creme_core.models import CremeEntity
from creme_core.views.generic import inner_popup


@login_required
def generic_add(request, entity_id, form_class, title):
    """
        @Permissions : Edit on entity that's will be linked to the action
    """
    entity = get_object_or_404(CremeEntity, pk=entity_id).get_real_entity()

    die_status = edit_object_or_die(request, entity)
    if die_status:
        return die_status

    if request.POST:
        assistant_form = form_class(entity, request.POST)

        if assistant_form.is_valid():
            assistant_form.save()
    else:
        assistant_form = form_class(entity=entity)

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {
                        'form':   assistant_form,
                        'title':  title % entity,
                       },
                       is_valid=assistant_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))

@login_required
def generic_edit(request, assistant_id, assistant_model, assistant_form, title):
    alert = get_object_or_404(assistant_model, pk=assistant_id)
    entity = alert.creme_entity

    die_status = edit_object_or_die(request, entity)
    if die_status:
        return die_status

    if request.POST:
        edit_form = assistant_form(entity, request.POST, instance=alert)

        if edit_form.is_valid():
            edit_form.save()
    else: # return page on GET request
        edit_form = assistant_form(entity=entity, instance=alert)

    return inner_popup(request, 'creme_core/generics/blockform/edit_popup.html',
                       {
                        'form':  edit_form,
                        'title': title % entity,
                       },
                       is_valid=edit_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))

#TODO: credentials ????
@login_required
def generic_delete(request, assistant_model, pk_key='id'):
    assistant = get_object_or_404(assistant_model, pk=request.POST.get(pk_key))
    assistant.delete()

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")
    else:
        return HttpResponseRedirect(assistant.creme_entity.get_absolute_url())
