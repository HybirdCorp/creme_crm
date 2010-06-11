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
from django.contrib.contenttypes.models import ContentType

from creme_core.views.generic import list_view, add_entity, view_entity_with_template
from creme_core.gui.last_viewed import change_page_for_last_viewed, change_page_for_last_item_viewed
from creme_core.entities_access.functions_for_permissions import add_view_or_die, get_view_or_die, edit_object_or_die

from commercial.models import Act
from commercial.forms.act import CreateForm, EditForm


@login_required
@get_view_or_die('commercial')
@add_view_or_die(ContentType.objects.get_for_model(Act), None, 'commercial')
def add(request):
    return add_entity(request, CreateForm)

#TODO: use generic edit_view ??? (removed useless imports too !!)
@login_required
@get_view_or_die('commercial')
def edit(request, act_id):
    act = get_object_or_404(Act, pk=act_id)

    die_status = edit_object_or_die(request, act)
    if die_status:
        return die_status

    if request.POST:
        form = EditForm(request.POST, instance=act)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect('/commercial/act/%s' % act_id)
    else:
        form = EditForm(instance=act)

    return render_to_response('creme_core/generics/blockform/edit.html',
                              {'form': form},
                              context_instance=RequestContext(request))

@login_required
@get_view_or_die('commercial')
def detailview(request, object_id):
    """
        @Permissions : Acces or Admin to document app & Read on current Act object
    """
    return view_entity_with_template(request,
                                     object_id,
                                     Act,
                                     '/commercial/act',
                                     'creme_core/generics/view_entity.html')

@login_required
@get_view_or_die('commercial')
@change_page_for_last_item_viewed
def listview(request):
    """
        @Permissions : Acces or Admin to commercial app
    """
    return list_view(request, Act, extra_dict={'add_url':'/commercial/act/add'})
