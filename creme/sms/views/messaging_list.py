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
from django.contrib.auth.decorators import login_required, permission_required

from creme_core.views.generic import add_entity, add_to_entity, edit_entity, view_entity_with_template, list_view
from creme_core.utils import get_from_POST_or_404

from sms.models import MessagingList
from sms.forms.messaging_list import MessagingListForm, AddContactsForm, AddContactsFromFilterForm


@login_required
@permission_required('sms')
@permission_required('sms.add_messaginglist')
def add(request):
    return add_entity(request, MessagingListForm)

def edit(request, mlist_id):
    return edit_entity(request, mlist_id, MessagingList, MessagingListForm, 'sms')

@login_required
@permission_required('sms')
def detailview(request, mlist_id):
    return view_entity_with_template(request, mlist_id, MessagingList,
                                     '/sms/messaging_list', 'sms/view_messaginglist.html')

@login_required
@permission_required('sms')
def listview(request):
    return list_view(request, MessagingList, extra_dict={'add_url': '/sms/messaging_list/add'})

def add_contacts(request, mlist_id):
    return add_to_entity(request, mlist_id, AddContactsForm,
                         _('New contacts for <%s>'), entity_class=MessagingList)

def add_contacts_from_filter(request, mlist_id):
    return add_to_entity(request, mlist_id, AddContactsFromFilterForm,
                         _('New contacts for <%s>'), entity_class=MessagingList)

@login_required
@permission_required('sms')
def _delete_aux(request, mlist_id, deletor):
    subobject_id   = get_from_POST_or_404(request.POST, 'id')
    messaging_list = get_object_or_404(MessagingList, pk=mlist_id)

    messaging_list.change_or_die(request.user)

    deletor(messaging_list, subobject_id)

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")

    return HttpResponseRedirect(messaging_list.get_absolute_url())

def delete_contact(request, mlist_id):
    return _delete_aux(request, mlist_id, lambda ml, contact_id: ml.contacts.remove(contact_id))

#def delete_organisation(request, mlist_id):
#    return _delete_aux(request, mlist_id, lambda ml, orga_id: ml.organisations.remove(orga_id))
#
#def delete_child(request, mlist_id):
#    return _delete_aux(request, mlist_id, lambda ml, child_id: ml.children.remove(child_id))
