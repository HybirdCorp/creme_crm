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

from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.contrib.auth.decorators import login_required

from creme_core.views.generic.popup import inner_popup


@login_required
def edit_entity(request, object_id, model, edit_form, app_name, template='creme_core/generics/blockform/edit.html'):
    if not request.user.has_perm(app_name):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("You don't have access to the app: %s" % app_name)

    entity = get_object_or_404(model, pk=object_id)
    entity.can_change_or_die(request.user)

    if request.method == 'POST':
        form = edit_form(request.POST, instance=entity)

        if form.is_valid():
            form.save()

            return HttpResponseRedirect(entity.get_absolute_url())
    else:
        form = edit_form(instance=entity)

    return render_to_response(template,
                              {
                                'form':   form,
                                'object': entity,
                              },
                              context_instance=RequestContext(request))

def edit_related_to_entity(request, pk, model, form_class, title_format):
    """Edit a model related to a CremeEntity.
    @param model A django model class that implements the method get_related_entity().
    @param model title_format A format unicode with an arg (for the related entity).
    """
    auxiliary = get_object_or_404(model, pk=pk)
    entity = auxiliary.get_related_entity()

    entity.can_change_or_die(request.user)

    if request.POST:
        edit_form = form_class(entity, request.POST, instance=auxiliary)

        if edit_form.is_valid():
            edit_form.save()
    else: # return page on GET request
        edit_form = form_class(entity=entity, instance=auxiliary)

    return inner_popup(request, 'creme_core/generics/blockform/edit_popup.html',
                       {
                        'form':  edit_form,
                        'title': title_format % entity,
                       },
                       is_valid=edit_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))
