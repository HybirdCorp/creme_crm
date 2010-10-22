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
from django.contrib.auth.decorators import login_required, permission_required

from creme_core.views.generic import inner_popup
from creme_core.utils import get_from_POST_or_404


@login_required
def generic_edit(request, assistant_id, assistant_model, assistant_form, title):
    alert = get_object_or_404(assistant_model, pk=assistant_id)
    entity = alert.creme_entity

    entity.can_change_or_die(request.user)

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
    assistant = get_object_or_404(assistant_model, pk=get_from_POST_or_404(request.POST, pk_key))
    assistant.delete()

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")

    return HttpResponseRedirect(assistant.creme_entity.get_absolute_url())
