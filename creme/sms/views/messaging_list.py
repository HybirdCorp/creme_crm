# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views.generic import (add_entity, add_to_entity,
        edit_entity, view_entity, list_view)
from creme.creme_core.utils import get_from_POST_or_404

from ..forms.messaging_list import MessagingListForm, AddContactsForm, AddContactsFromFilterForm
from ..models import MessagingList


@login_required
@permission_required('sms')
@permission_required('sms.add_messaginglist')
def add(request):
    return add_entity(request, MessagingListForm,
                      extra_template_dict={'submit_label': _('Save the messaging list')},
                     )

@login_required
@permission_required('sms')
def edit(request, mlist_id):
    return edit_entity(request, mlist_id, MessagingList, MessagingListForm)

@login_required
@permission_required('sms')
def detailview(request, mlist_id):
    return view_entity(request, mlist_id, MessagingList, '/sms/messaging_list', 'sms/view_messaginglist.html')

@login_required
@permission_required('sms')
def listview(request):
    return list_view(request, MessagingList, extra_dict={'add_url': '/sms/messaging_list/add'})

@login_required
@permission_required('sms')
def add_contacts(request, mlist_id):
    return add_to_entity(request, mlist_id, AddContactsForm,
                         ugettext('New contacts for <%s>'),
                         entity_class=MessagingList,
                        )

@login_required
@permission_required('sms')
def add_contacts_from_filter(request, mlist_id):
    return add_to_entity(request, mlist_id, AddContactsFromFilterForm,
                         ugettext('New contacts for <%s>'),
                         entity_class=MessagingList,
                        )

@login_required
@permission_required('sms')
def _delete_aux(request, mlist_id, deletor):
    subobject_id   = get_from_POST_or_404(request.POST, 'id')
    messaging_list = get_object_or_404(MessagingList, pk=mlist_id)

    request.user.has_perm_to_change_or_die(messaging_list)

    deletor(messaging_list, subobject_id)

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")

    return redirect(messaging_list)

def delete_contact(request, mlist_id):
    return _delete_aux(request, mlist_id, lambda ml, contact_id: ml.contacts.remove(contact_id))

#def delete_organisation(request, mlist_id):
#    return _delete_aux(request, mlist_id, lambda ml, orga_id: ml.organisations.remove(orga_id))
#
#def delete_child(request, mlist_id):
#    return _delete_aux(request, mlist_id, lambda ml, child_id: ml.children.remove(child_id))
