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
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType

from creme_core.entities_access.functions_for_permissions import get_view_or_die, add_view_or_die, edit_object_or_die
from creme_core.views.generic import add_entity, edit_entity, view_entity_with_template, list_view, inner_popup

from sms.models import SendList
from sms.forms.sendlist import SendListForm, AddContactsForm, AddContactsFromFilterForm


@login_required
@get_view_or_die('sms')
@add_view_or_die(ContentType.objects.get_for_model(SendList), None, 'sms')
def add(request):
    return add_entity(request, SendListForm)

def edit(request, id):
    return edit_entity(request, id, SendList, SendListForm, 'sms')

@login_required
@get_view_or_die('sms')
def detailview(request, id):
    return view_entity_with_template(request, id, SendList,
                                     '/sms/sendlist', 'sms/view_sendlist.html')

@login_required
@get_view_or_die('sms')
def listview(request):
    return list_view(request, SendList, extra_dict={'add_url': '/sms/sendlist/add'})

@login_required
@get_view_or_die('sms')
def _add_aux(request, id, form_class, title):
    sendlist = get_object_or_404(SendList, pk=id)

    die_status = edit_object_or_die(request, sendlist)
    if die_status:
        return die_status

    if request.POST:
        recip_add_form = form_class(sendlist, request.POST)

        if recip_add_form.is_valid():
            recip_add_form.save()
    else:
        recip_add_form = form_class(sendlist=sendlist)

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {
                        'form':  recip_add_form,
                        'title': title % sendlist,
                       },
                       is_valid=recip_add_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))

def add_contacts(request, id):
    return _add_aux(request, id, AddContactsForm, _('New contacts for <%s>'))

def add_contacts_from_filter(request, id):
    return _add_aux(request, id, AddContactsFromFilterForm, _('New contacts for <%s>'))

@login_required
@get_view_or_die('sms')
def _delete_aux(request, sendlist_id, deletor):
    subobject_id = request.POST.get('id')
    sendlist = get_object_or_404(SendList, pk=sendlist_id)

    die_status = edit_object_or_die(request, sendlist)
    if die_status:
        return die_status

    deletor(sendlist, subobject_id)

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")

    return HttpResponseRedirect(sendlist.get_absolute_url())

def delete_contact(request, sendlist_id):
    return _delete_aux(request, sendlist_id, lambda ml, contact_id: ml.contacts.remove(contact_id))

#def delete_organisation(request, sendlist_id):
#    return _delete_aux(request, sendlist_id, lambda ml, orga_id: ml.organisations.remove(orga_id))
#
#def delete_child(request, sendlist_id):
#    return _delete_aux(request, sendlist_id, lambda ml, child_id: ml.children.remove(child_id))
